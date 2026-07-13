from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from engine.process_manager import manager

router = APIRouter()

class RunRequest(BaseModel):
    preset_name: str

@router.post("/run")
def start_run(req: RunRequest):
    from core.config import get_preset
    preset = get_preset(req.preset_name)
    if not preset:
        raise HTTPException(404, f"预设不存在: {req.preset_name}")
    ep = manager.start_engine(mode="script", preset_name=req.preset_name)
    return {"status": "ok", "message": f"已启动: {req.preset_name}", "execution_id": ep.execution_id}

@router.post("/stop")
def stop_run(execution_id: str = ""):
    if execution_id:
        ok = manager.stop_engine(execution_id)
        if not ok:
            raise HTTPException(404, f"引擎实例不存在: {execution_id}")
        return {"status": "ok", "message": f"已停止: {execution_id}"}
    # 兼容：不指定 execution_id 时停止所有 script 引擎
    engines = manager.list_engines()
    for e in engines:
        if e["mode"] == "script" and e["status"] == "running":
            manager.stop_engine(e["execution_id"])
    return {"status": "ok", "message": "已停止所有脚本引擎"}

@router.get("/status")
def get_status(execution_id: str = ""):
    if execution_id:
        ep = manager.get_engine(execution_id)
        if not ep:
            raise HTTPException(404, f"引擎实例不存在: {execution_id}")
        return {
            "execution_id": ep.execution_id,
            "mode": ep.mode,
            "status": ep.status,
            "logs": ep.logs[-50:],
            "duration_ms": ep.duration_ms,
        }
    # 兼容：返回最近一个 script 引擎的状态
    engines = manager.list_engines()
    script_engines = [e for e in engines if e["mode"] == "script"]
    if not script_engines:
        return {"status": "idle", "logs": []}
    latest = script_engines[-1]
    ep = manager.get_engine(latest["execution_id"])
    if not ep:
        return {"status": "idle", "logs": []}
    return {
        "execution_id": ep.execution_id,
        "status": ep.status,
        "logs": ep.logs[-50:],
        "duration_ms": ep.duration_ms,
    }
