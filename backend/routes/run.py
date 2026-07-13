from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import threading
from typing import Optional
from engine.engine import ScriptEngine

router = APIRouter()
engine = ScriptEngine()
_engine_lock = threading.Lock()  # 保护引擎实例的并发访问
_active_run_thread: Optional[threading.Thread] = None


class RunRequest(BaseModel):
    preset_name: str


@router.post("/run")
def start_run(req: RunRequest):
    global _active_run_thread
    from core.config import get_preset
    with _engine_lock:
        if _active_run_thread and _active_run_thread.is_alive():
            raise HTTPException(409, "已有流程在运行中，请先停止")
        preset = get_preset(req.preset_name)
        if not preset:
            raise HTTPException(404, f"预设不存在: {req.preset_name}")
        thread = threading.Thread(target=engine.run, args=(preset,), kwargs={"chain": True})
        thread.daemon = True
        _active_run_thread = thread
        thread.start()
        return {"status": "ok", "message": f"已启动: {req.preset_name}"}


@router.post("/stop")
def stop_run():
    global _active_run_thread
    with _engine_lock:
        engine.stop()
        if _active_run_thread and _active_run_thread.is_alive():
            _active_run_thread.join(timeout=3)
        _active_run_thread = None
    return {"status": "ok", "message": "已停止"}


@router.get("/status")
def get_status():
    with _engine_lock:
        return engine.monitor()
