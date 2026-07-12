from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import threading
from engine.engine import ScriptEngine

router = APIRouter()
engine = ScriptEngine()

class RunRequest(BaseModel):
    preset_name: str

@router.post("/run")
def start_run(req: RunRequest):
    from core.config import get_preset
    preset = get_preset(req.preset_name)
    if not preset:
        raise HTTPException(404, f"预设不存在: {req.preset_name}")
    thread = threading.Thread(target=engine.run, args=(preset,), kwargs={"chain": True})
    thread.daemon = True
    thread.start()
    return {"status": "ok", "message": f"已启动: {req.preset_name}"}

@router.post("/stop")
def stop_run():
    engine.stop()
    return {"status": "ok", "message": "已停止"}

@router.get("/status")
def get_status():
    return engine.monitor()
