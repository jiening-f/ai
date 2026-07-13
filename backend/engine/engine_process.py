"""
引擎独立子进程入口

通过 subprocess 启动，与父进程（API 服务）通过 stdin/stdout JSON 行协议通信。

协议格式（每行一个 JSON）：
  → 子进程发送: {"type": "log|status|done|error|heartbeat", "data": ...}
  ← 父进程发送: {"type": "stop|pause|resume", "data": ...}
"""
import json
import sys
import os
import time
import argparse
import threading
from pathlib import Path

# 确保 backend/ 在 Python path 中
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


def send(msg: dict):
    """向父进程发送 JSON 消息（单行）"""
    line = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def listen(stop_event: threading.Event):
    """在独立线程中监听父进程的指令"""
    try:
        for line in sys.stdin:
            if stop_event.is_set():
                break
            line = line.strip()
            if not line:
                continue
            try:
                cmd = json.loads(line)
                _handle_command(cmd)
            except json.JSONDecodeError:
                pass
    except (EOFError, OSError):
        pass


_engine_instance = None
_stop_requested = False


def _handle_command(cmd: dict):
    global _stop_requested
    cmd_type = cmd.get("type", "")
    if cmd_type == "stop":
        _stop_requested = True
        if _engine_instance is not None:
            _engine_instance.stop()
    elif cmd_type == "pause":
        send({"type": "log", "data": "[engine] pause 指令已收到，暂不支持"})
    elif cmd_type == "resume":
        send({"type": "log", "data": "[engine] resume 指令已收到，暂不支持"})


def run_script_engine(preset_name: str):
    """运行 ScriptEngine"""
    global _engine_instance, _stop_requested
    send({"type": "log", "data": f"[engine] 启动 ScriptEngine，预设: {preset_name}"})

    from engine.engine import ScriptEngine
    from core.config import get_preset

    preset = get_preset(preset_name)
    if not preset:
        send({"type": "error", "data": f"预设不存在: {preset_name}"})
        return

    _engine_instance = ScriptEngine()

    def heartbeat_loop():
        while not _stop_requested:
            time.sleep(15)
            try:
                status = _engine_instance.monitor() if hasattr(_engine_instance, 'monitor') else {}
            except Exception:
                status = {}
            send({"type": "heartbeat", "data": status})

    hb = threading.Thread(target=heartbeat_loop, daemon=True)
    hb.start()

    try:
        engine = _engine_instance
        send({"type": "status", "data": "running"})

        def capture_log(msg: str):
            send({"type": "log", "data": msg})

        original_run = engine.run
        # 包装 run 以捕获日志
        _run_with_log(engine, preset, on_log=capture_log)

        send({"type": "status", "data": "done"})
        send({"type": "done", "data": {"message": f"预设 {preset_name} 执行完成"}})
    except Exception as e:
        send({"type": "error", "data": str(e)})
        send({"type": "status", "data": "error"})


def _run_with_log(engine, preset, on_log=None):
    """执行 ScriptEngine.run 并捕获日志"""
    from engine.engine import ScriptEngine
    original_monitor = engine.monitor

    log_buffer = []

    def patched_monitor():
        info = original_monitor()
        info["logs"] = list(log_buffer)
        log_buffer.clear()
        return info

    engine.monitor = patched_monitor

    # ScriptEngine.run 本身没有 on_log 回调，我们通过 monitor 收集日志
    def log_thread():
        while not _stop_requested:
            time.sleep(0.5)
            try:
                info = engine.monitor()
                if info and info.get("logs"):
                    for msg in info["logs"]:
                        if on_log:
                            on_log(msg)
            except Exception:
                pass

    lt = threading.Thread(target=log_thread, daemon=True)
    lt.start()

    engine.run(preset, chain=True)


def run_node_engine(flow_json: str):
    """运行 NodeEngine"""
    global _engine_instance, _stop_requested
    send({"type": "log", "data": "[engine] 启动 NodeEngine"})

    from engine.node_engine import NodeEngine
    import json as _json

    flow_data = _json.loads(flow_json)
    flow = _rebuild_node_flow(flow_data)

    _engine_instance = NodeEngine()

    def on_log(msg: str):
        send({"type": "log", "data": msg})

    def heartbeat_loop():
        while not _stop_requested:
            time.sleep(15)
            send({"type": "heartbeat", "data": {"running": not _stop_requested}})

    hb = threading.Thread(target=heartbeat_loop, daemon=True)
    hb.start()

    try:
        send({"type": "status", "data": "running"})
        _engine_instance.run(flow, on_log=on_log)
        send({"type": "status", "data": "done"})
        send({"type": "done", "data": {"message": "节点流程执行完成"}})
    except Exception as e:
        send({"type": "error", "data": str(e)})
        send({"type": "status", "data": "error"})


def _rebuild_node_flow(data: dict):
    """从 JSON dict 重建 NodeFlow 领域对象"""
    from engine.node_engine import NodeFlow, MapConfig, FeatureNode, DetectType, Decision

    flow = NodeFlow(
        loop_enabled=data.get("loop_enabled", True),
        max_loops=data.get("max_loops", 0),
    )
    for m_data in data.get("maps", []):
        features = []
        for f_data in m_data.get("features", []):
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


def main():
    parser = argparse.ArgumentParser(description="引擎子进程")
    parser.add_argument("--mode", required=True, choices=["script", "node"],
                        help="script: ScriptEngine | node: NodeEngine")
    parser.add_argument("--preset-name", default="", help="ScriptEngine 模式下的预设名")
    parser.add_argument("--flow-json", default="", help="NodeEngine 模式下的流程 JSON")
    args = parser.parse_args()

    stop_event = threading.Event()
    listener = threading.Thread(target=listen, args=(stop_event,), daemon=True)
    listener.start()

    send({"type": "log", "data": f"[engine] 子进程已启动，模式: {args.mode}"})

    if args.mode == "script":
        run_script_engine(args.preset_name)
    else:
        run_node_engine(args.flow_json)

    stop_event.set()


if __name__ == "__main__":
    main()
