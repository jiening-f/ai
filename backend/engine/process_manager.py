"""API 侧引擎进程生命周期管理器（单例）"""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Optional

# ── 常量 ──
_HEARTBEAT_TIMEOUT = 30       # 秒，超过此值判定引擎死亡
_MAX_RETRIES = 3              # 崩溃后最大重试次数
_HEARTBEAT_CHECK_INTERVAL = 10  # 心跳检查周期（秒）

# ── 全局状态（模块级单例）──
_lock = threading.Lock()
_processes: dict[str, dict] = {}      # execution_id → 进程信息
_heartbeats: dict[str, float] = {}    # execution_id → 最后心跳时间戳
_shutdown_event = threading.Event()


# ── 内部工具 ──

def _engine_script_path() -> str:
    """返回 engine_process.py 的绝对路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_process.py")


def _sanitize_config(config: dict) -> dict:
    """
    清洗配置中的不可序列化字段（例如数据库对象、回调函数）。
    保留原始配置的副本供重试时使用。
    """
    safe = {}
    for k, v in config.items():
        if k in ("preset", "flow", "chain", "region", "hwnd",
                 "override_max_runs", "override_ri", "game_hwnd"):
            safe[k] = v
    return safe


# ── 公开 API ──

def start_engine(
    execution_id: int,
    mode: str,
    config: dict,
    api_url: str = "http://127.0.0.1:8765",
) -> dict:
    """启动引擎独立子进程

    Args:
        execution_id: 执行记录 ID
        mode: "script" | "node"
        config: 引擎配置字典
        api_url: API 服务器地址

    Returns:
        {"status": "ok", "message": "..."} 或 {"status": "error", "message": "..."}
    """
    eid = str(execution_id)
    with _lock:
        if eid in _processes:
            existing = _processes[eid]
            if existing["process"].poll() is None:
                return {
                    "status": "error",
                    "message": f"引擎 {execution_id} 已在运行 (PID: {existing['pid']})",
                }
            # 进程已退出，清理旧记录
            _processes.pop(eid, None)
            _heartbeats.pop(eid, None)

        config_json = json.dumps(config, ensure_ascii=False)
        script_path = _engine_script_path()

        proc = subprocess.Popen(
            [sys.executable, script_path,
             "--api-url", api_url,
             "--execution-id", str(execution_id),
             "--mode", mode,
             "--config", config_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        info = {
            "process": proc,
            "mode": mode,
            "status": "starting",
            "retries": 0,
            "started_at": time.time(),
            "pid": proc.pid,
            "config": config,      # 保留以供重试
            "api_url": api_url,
        }
        _processes[eid] = info
        _heartbeats[eid] = time.time()

    return {"status": "ok", "message": f"引擎 {execution_id} 已启动 (PID: {proc.pid})"}


def stop_engine(execution_id: int) -> dict:
    """停止引擎子进程

    先尝试优雅终止（SIGTERM），超时后强制杀死。
    """
    eid = str(execution_id)
    with _lock:
        info = _processes.get(eid)
        if not info:
            return {"status": "ok", "message": f"引擎 {execution_id} 不存在"}

        proc = info["process"]

        # 检查进程是否已自行退出
        if proc.poll() is not None:
            _processes.pop(eid, None)
            _heartbeats.pop(eid, None)
            return {"status": "ok", "message": f"引擎 {execution_id} 已自行退出"}

        try:
            if sys.platform == "win32":
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass

        info["status"] = "stopped"
        _processes.pop(eid, None)
        _heartbeats.pop(eid, None)

    return {"status": "ok", "message": f"引擎 {execution_id} 已停止"}


def update_heartbeat(execution_id: int) -> None:
    """更新心跳时间戳（由 WebSocket handler 在接收心跳时调用）"""
    _heartbeats[str(execution_id)] = time.time()


def update_status(execution_id: int, status: str) -> None:
    """更新引擎状态（由 WebSocket handler 在收到状态变更时调用）"""
    eid = str(execution_id)
    with _lock:
        info = _processes.get(eid)
        if info:
            info["status"] = status
            if status in ("completed", "error", "stopped", "cancelled"):
                _heartbeats.pop(eid, None)


def get_engine_status(execution_id: int) -> Optional[dict]:
    """查询指定引擎的状态"""
    eid = str(execution_id)
    with _lock:
        info = _processes.get(eid)
        if not info:
            return None
        proc = info["process"]
        return_code = proc.poll()
        return {
            "execution_id": execution_id,
            "mode": info["mode"],
            "status": info["status"],
            "pid": info["pid"],
            "started_at": info["started_at"],
            "retries": info["retries"],
            "alive": return_code is None,
            "return_code": return_code,
        }


def list_engines() -> list[dict]:
    """列出所有活跃（或最近活跃）的引擎"""
    with _lock:
        return [
            {
                "execution_id": int(eid),
                "mode": info["mode"],
                "status": info["status"],
                "pid": info["pid"],
                "started_at": info["started_at"],
                "retries": info["retries"],
            }
            for eid, info in _processes.items()
        ]


def shutdown_all() -> None:
    """清理所有引擎进程（FastAPI lifespan 关闭时调用）"""
    _shutdown_event.set()
    for eid in list(_processes.keys()):
        try:
            stop_engine(int(eid))
        except Exception:
            pass


# ══ 心跳检测后台线程 ══════════════════════════════

def _check_heartbeats_loop() -> None:
    """定期检查心跳，超时或死亡进程进行重试或清理"""
    while not _shutdown_event.is_set():
        _shutdown_event.wait(_HEARTBEAT_CHECK_INTERVAL)
        if _shutdown_event.is_set():
            break

        now = time.time()
        to_cleanup = []

        with _lock:
            for eid, last_beat in list(_heartbeats.items()):
                info = _processes.get(eid)
                if not info:
                    continue

                proc = info["process"]
                return_code = proc.poll()

                if return_code is not None:
                    # 进程已退出
                    if info["retries"] < _MAX_RETRIES:
                        to_cleanup.append((eid, info, "crashed"))
                    else:
                        info["status"] = "failed"
                        _heartbeats.pop(eid, None)
                elif now - last_beat > _HEARTBEAT_TIMEOUT:
                    # 心跳超时
                    if info["retries"] < _MAX_RETRIES:
                        to_cleanup.append((eid, info, "timeout"))
                    else:
                        info["status"] = "lost"
                        _heartbeats.pop(eid, None)

        for eid, info, reason in to_cleanup:
            try:
                proc = info["process"]
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)
            except Exception:
                pass

            info["retries"] += 1
            info["status"] = f"restarting (retry {info['retries']}/{_MAX_RETRIES})"

            # 重试：重新启动子进程
            try:
                result = start_engine(
                    execution_id=int(eid),
                    mode=info["mode"],
                    config=info["config"],
                    api_url=info.get("api_url", "http://127.0.0.1:8765"),
                )
                if result["status"] == "ok":
                    with _lock:
                        if eid in _processes:
                            _processes[eid]["retries"] = info["retries"]
            except Exception as exc:
                print(f"[process_manager] 重试引擎 {eid} 失败: {exc}", file=sys.stderr)


# 启动后台心跳检查
_heartbeat_thread = threading.Thread(
    target=_check_heartbeats_loop,
    daemon=True,
    name="engine-hb-checker",
)
_heartbeat_thread.start()
