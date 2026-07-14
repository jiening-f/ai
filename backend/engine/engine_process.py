"""独立引擎子进程入口 — 通过 CLI 参数启动，连接 API WebSocket 通信"""
import argparse
import asyncio
import json
import os
import sys
import threading
import time
from queue import Queue, Empty
from typing import Any, Optional

import websockets

# ── 路径引导 ──────────────────────────────────────
# 项目根目录 ai/ 和 backend/ 均加入 sys.path，与现有模块的导入风格保持一致
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)
_BACKEND_ROOT = os.path.join(_PROJ_ROOT, "backend")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from engine.engine import ScriptEngine
from engine.node_engine import (
    NodeEngine, NodeFlow, MapConfig, FeatureNode,
    DetectType, Decision,
)


# ══ 序列化工具 ════════════════════════════════════

def _dict_to_nodeflow(data: dict) -> NodeFlow:
    """字典 → NodeFlow 领域对象"""
    flow = NodeFlow(
        loop_enabled=data.get("loop_enabled", True),
        max_loops=data.get("max_loops", 0),
    )
    for m_data in data.get("maps", []):
        if not isinstance(m_data, dict):
            continue
        features = []
        for f_data in m_data.get("features", []):
            if not isinstance(f_data, dict):
                continue
            try:
                dt = DetectType(f_data.get("detect_type", "text"))
            except ValueError:
                dt = DetectType.TEXT
            try:
                om = Decision(f_data.get("on_match", "continue"))
            except ValueError:
                om = Decision.CONTINUE
            try:
                omm = Decision(f_data.get("on_mismatch", "continue"))
            except ValueError:
                omm = Decision.CONTINUE
            features.append(FeatureNode(
                id=f_data.get("id", ""),
                map_id=f_data.get("map_id", m_data.get("id", "")),
                detect_type=dt,
                detect_value=f_data.get("detect_value", ""),
                on_match=om,
                on_mismatch=omm,
                enabled=f_data.get("enabled", True),
            ))
        flow.maps.append(MapConfig(
            id=m_data.get("id", ""),
            name=m_data.get("name", ""),
            enabled=m_data.get("enabled", True),
            features=features,
        ))
    return flow


# ══ WebSocket 客户端 ═══════════════════════════════

class EngineWsClient:
    """引擎进程端 WebSocket 客户端 — 与 API 进程双向通信"""

    def __init__(self, api_url: str, execution_id: str, mode: str):
        self.api_url = api_url.rstrip("/")
        ws_url = f"{self.api_url}/api/ws/engine/{execution_id}"
        ws_url = ws_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = ws_url
        self.execution_id = execution_id
        self.mode = mode
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._send_queue: "Queue[dict]" = Queue()
        self._running = True

    async def _connect_with_retry(self) -> None:
        """连接 API WebSocket，失败时自动重试最多 5 次"""
        max_attempts = 5
        base_delay = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                self.ws = await websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    open_timeout=10,
                )
                await self.ws.send(json.dumps({
                    "type": "engine_hello",
                    "data": {
                        "execution_id": self.execution_id,
                        "mode": self.mode,
                    },
                }))
                return
            except (OSError, asyncio.TimeoutError, websockets.WebSocketException) as exc:
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"[engine_process] 连接失败 (第{attempt}次), {delay:.0f}s 后重试: {exc}",
                          file=sys.stderr)
                    await asyncio.sleep(delay)
                else:
                    print(f"[engine_process] 连接失败，已达最大重试次数: {exc}",
                          file=sys.stderr)
                    raise

    def send(self, msg: dict) -> None:
        """线程安全的消息入队（从引擎同步回调中调用）"""
        self._send_queue.put(msg)

    async def _drain_send_queue(self) -> None:
        """从发送队列取出消息并写入 WebSocket"""
        while self._running:
            try:
                msg = self._send_queue.get(timeout=0.2)
                try:
                    await self.ws.send(json.dumps(msg))
                except websockets.WebSocketException as exc:
                    print(f"[engine_process] 发送失败: {exc}", file=sys.stderr)
                    self._send_queue.put(msg)
                    await asyncio.sleep(1)
            except Empty:
                continue

    async def _listen_control(self, engine) -> None:
        """监听 API 发来的控制指令"""
        while self._running and self.ws:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                data = json.loads(raw)
                cmd = data.get("type", "")
                if cmd == "stop":
                    engine.stop()
                    self.send({
                        "type": "status_change",
                        "data": {"status": "stopped"},
                    })
                elif cmd == "pause" and hasattr(engine, "pause"):
                    engine.pause()
                elif cmd == "resume" and hasattr(engine, "resume"):
                    engine.resume()
            except asyncio.TimeoutError:
                continue
            except websockets.WebSocketException:
                break
            except Exception as exc:
                print(f"[engine_process] 控制指令异常: {exc}", file=sys.stderr)
                break

    async def _heartbeat_loop(self) -> None:
        """每 15 秒发送一次心跳"""
        while self._running:
            await asyncio.sleep(15)
            if self.ws:
                try:
                    await self.ws.send(json.dumps({"type": "heartbeat"}))
                except websockets.WebSocketException:
                    break

    async def run(self, config: dict) -> None:
        """主流程：连接 WS → 启动引擎 → 等待完成"""
        await self._connect_with_retry()

        # ── 回调封装（引擎同步回调 → WS 消息）──
        def on_log(msg: str) -> None:
            self.send({
                "type": "log",
                "data": {"message": msg, "execution_id": self.execution_id},
            })

        def on_done() -> None:
            self.send({
                "type": "status_change",
                "data": {"status": "completed"},
            })

        # ── 创建引擎实例 ──
        engine = None
        engine_coro = None

        if self.mode == "script":
            engine = ScriptEngine()
            preset = config.get("preset", {})
            chain = config.get("chain", True)
            region = config.get("region")
            hwnd = config.get("hwnd")
            override_max_runs = config.get("override_max_runs")
            override_ri = config.get("override_ri")
            game_hwnd = config.get("game_hwnd")

            def run_script():
                engine.run(
                    preset,
                    chain=chain,
                    on_log=on_log,
                    on_done=on_done,
                    region=region,
                    hwnd=hwnd,
                    override_max_runs=override_max_runs,
                    override_ri=override_ri,
                    game_hwnd=game_hwnd,
                )

            engine_coro = asyncio.get_event_loop().run_in_executor(None, run_script)

        elif self.mode == "node":
            engine = NodeEngine()
            flow = _dict_to_nodeflow(config.get("flow", {}))

            def run_node():
                engine.run(flow, on_log=on_log)

            engine_coro = asyncio.get_event_loop().run_in_executor(None, run_node)

        if engine is None or engine_coro is None:
            self.send({
                "type": "status_change",
                "data": {
                    "status": "error",
                    "error_message": f"未知引擎模式: {self.mode}",
                },
            })
            return

        # 通知 API 引擎已启动
        self.send({
            "type": "status_change",
            "data": {"status": "running"},
        })

        # 启动并发任务
        drain_task = asyncio.create_task(self._drain_send_queue())
        control_task = asyncio.create_task(self._listen_control(engine))
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 等待引擎执行完成
        try:
            await engine_coro
            if self.mode == "node":
                # NodeEngine 没有 on_done 回调，在这里发送完成状态
                self.send({
                    "type": "status_change",
                    "data": {"status": "completed"},
                })
        except Exception as exc:
            error_msg = str(exc)
            print(f"[engine_process] 引擎异常: {error_msg}", file=sys.stderr)
            self.send({
                "type": "status_change",
                "data": {
                    "status": "error",
                    "error_message": error_msg,
                },
            })
        finally:
            self._running = False
            # 等待剩余消息发送完成
            await asyncio.sleep(0.5)
            for task in (drain_task, control_task, heartbeat_task):
                task.cancel()
            await asyncio.gather(
                drain_task, control_task, heartbeat_task,
                return_exceptions=True,
            )
            if self.ws:
                await self.ws.close()

    async def close(self) -> None:
        self._running = False
        if self.ws:
            await self.ws.close()


# ══ CLI ════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multica 独立引擎子进程")
    parser.add_argument(
        "--api-url", required=True,
        help="API 服务器地址，如 http://127.0.0.1:8765",
    )
    parser.add_argument("--execution-id", required=True, help="执行记录 ID")
    parser.add_argument(
        "--mode", required=True, choices=["script", "node"],
        help="引擎模式（script=脚本引擎, node=节点引擎）",
    )
    parser.add_argument("--config", required=True, help="引擎配置 JSON 字符串")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = json.loads(args.config)

    # Windows 下使用 Selector 事件循环以兼容子进程
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(EngineWsClient(
        api_url=args.api_url,
        execution_id=args.execution_id,
        mode=args.mode,
    ).run(config))


if __name__ == "__main__":
    main()
