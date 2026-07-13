"""
进程生命周期管理器（单例）

管理引擎子进程的创建、监控、终止。所有引擎操作统一通过此模块。
"""
import subprocess
import json
import os
import time
import threading
import signal
from pathlib import Path
from typing import Optional


class EngineProcess:
    """单个引擎进程的封装"""

    def __init__(self, execution_id: str, mode: str, process: subprocess.Popen):
        self.execution_id = execution_id
        self.mode = mode  # "script" | "node"
        self.process = process
        self.status = "running"  # running | done | error | stopped
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self.last_heartbeat = time.time()
        self.error_message: Optional[str] = None
        self.logs: list[str] = []

    @property
    def duration_ms(self) -> int:
        end = self.finished_at or time.time()
        return int((end - self.started_at) * 1000)

    def is_alive(self) -> bool:
        return self.process.poll() is None


class ProcessManager:
    """引擎进程管理器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._engines: dict[str, EngineProcess] = {}
        self._next_id = 1
        self._engine_lock = threading.Lock()
        self._shutdown_flag = False

        # 心跳检测后台线程
        self._hb_thread = threading.Thread(target=self._heartbeat_check, daemon=True)
        self._hb_thread.start()

    def _next_execution_id(self) -> str:
        with self._engine_lock:
            eid = f"engine-{self._next_id}"
            self._next_id += 1
        return eid

    def start_engine(self, mode: str, preset_name: str = "", flow_json: str = "") -> EngineProcess:
        """启动一个引擎子进程"""
        execution_id = self._next_execution_id()
        engine_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_process.py")

        cmd = [sys.executable, engine_py, "--mode", mode]
        if preset_name:
            cmd += ["--preset-name", preset_name]
        if flow_json:
            cmd += ["--flow-json", flow_json]

        # 启动子进程（stdin/stdout 管道）
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # backend/
        )

        ep = EngineProcess(execution_id, mode, process)

        # 启动 stdout 读取线程
        reader = threading.Thread(
            target=self._read_stdout,
            args=(ep,),
            daemon=True,
        )
        reader.start()

        with self._engine_lock:
            self._engines[execution_id] = ep

        return ep

    def stop_engine(self, execution_id: str, timeout: float = 5.0) -> bool:
        """停止指定的引擎进程"""
        with self._engine_lock:
            ep = self._engines.get(execution_id)
            if not ep:
                return False

        if not ep.is_alive():
            ep.status = "stopped"
            ep.finished_at = time.time()
            return True

        # 发送 stop 指令
        try:
            stop_cmd = {"type": "stop"}
            ep.process.stdin.write(json.dumps(stop_cmd) + "\n")
            ep.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

        # 等待进程结束
        try:
            ep.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            ep.process.kill()
            ep.process.wait()

        ep.status = "stopped"
        ep.finished_at = time.time()
        return True

    def stop_all(self, timeout: float = 5.0):
        """停止所有引擎进程"""
        self._shutdown_flag = True
        with self._engine_lock:
            eids = list(self._engines.keys())
        for eid in eids:
            self.stop_engine(eid, timeout=timeout)

    def get_engine(self, execution_id: str) -> Optional[EngineProcess]:
        with self._engine_lock:
            return self._engines.get(execution_id)

    def list_engines(self) -> list[dict]:
        with self._engine_lock:
            return [
                {
                    "execution_id": ep.execution_id,
                    "mode": ep.mode,
                    "status": ep.status,
                    "started_at": ep.started_at,
                    "duration_ms": ep.duration_ms,
                    "has_error": ep.error_message is not None,
                }
                for ep in self._engines.values()
            ]

    def _read_stdout(self, ep: EngineProcess):
        """在后台线程读取子进程 stdout（JSON 行协议）"""
        try:
            for line in ep.process.stdout:
                if self._shutdown_flag:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    self._handle_message(ep, msg)
                except json.JSONDecodeError:
                    ep.logs.append(f"[parse error] {line[:200]}")
        except (IOError, OSError, ValueError):
            pass
        finally:
            # 进程结束，更新状态
            ep.finished_at = time.time()
            if ep.status == "running":
                rc = ep.process.poll()
                if rc is not None and rc != 0:
                    ep.status = "error"
                    ep.error_message = f"进程退出，code={rc}"
                else:
                    ep.status = "done"

    def _handle_message(self, ep: EngineProcess, msg: dict):
        """处理子进程发来的消息"""
        msg_type = msg.get("type", "")
        data = msg.get("data", "")

        if msg_type == "log":
            ep.logs.append(str(data))

        elif msg_type == "status":
            ep.status = str(data)

        elif msg_type == "heartbeat":
            ep.last_heartbeat = time.time()

        elif msg_type == "error":
            ep.status = "error"
            ep.error_message = str(data)

        elif msg_type == "done":
            ep.status = "done"
            ep.finished_at = time.time()

    def _heartbeat_check(self):
        """后台心跳检测，超时 30 秒的进程标记为死亡"""
        while not self._shutdown_flag:
            time.sleep(10)
            now = time.time()
            with self._engine_lock:
                for ep in list(self._engines.values()):
                    if ep.status == "running" and (now - ep.last_heartbeat) > 30:
                        if not ep.is_alive():
                            ep.status = "error"
                            ep.error_message = "心跳超时，进程已死亡"
                            ep.finished_at = time.time()


# 全局单例
manager = ProcessManager()
