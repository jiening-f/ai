from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.engine.process_manager import (
    start_engine,
    stop_engine,
    get_engine_status,
)

router = APIRouter()

# 通过进程管理器启动的脚本执行引擎
_EXECUTION_ID: Optional[int] = None


class RunRequest(BaseModel):
    preset_name: str


class RunResponse(BaseModel):
    status: str
    message: str
    execution_id: Optional[int] = None


@router.post("/run")
def start_run(req: RunRequest):
    """启动预设执行 — 通过 EngineProcessManager 启动独立子进程"""
    from core.config import get_preset
    preset = get_preset(req.preset_name)
    if not preset:
        raise HTTPException(404, f"预设不存在: {req.preset_name}")

    # 生成一个简单的 execution_id（生产环境应由数据库生成）
    global _EXECUTION_ID
    import random
    execution_id = _EXECUTION_ID = random.randint(10000, 99999)

    config = {
        "preset": preset,
        "chain": True,
    }

    result = start_engine(
        execution_id=execution_id,
        mode="script",
        config=config,
    )

    if result["status"] == "error":
        raise HTTPException(409, result["message"])

    return RunResponse(
        status="ok",
        message=f"已启动: {req.preset_name} (execution_id={execution_id})",
        execution_id=execution_id,
    )


@router.post("/stop")
def stop_run():
    """停止当前运行的脚本引擎"""
    if _EXECUTION_ID is None:
        return {"status": "ok", "message": "没有正在运行的引擎"}

    result = stop_engine(_EXECUTION_ID)
    return {"status": "ok", "message": result["message"]}


@router.get("/status")
def get_run_status():
    """查询当前脚本引擎状态"""
    if _EXECUTION_ID is None:
        return {"status": "stopped", "action": "", "error": ""}

    status = get_engine_status(_EXECUTION_ID)
    if status is None:
        return {"status": "stopped", "action": "", "error": ""}

    return {
        "status": status["status"],
        "action": "",
        "error": "",
        "pid": status["pid"],
        "alive": status["alive"],
    }
