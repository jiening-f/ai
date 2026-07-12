"""执行 API — 对接数据库 Service 层"""

import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import threading
from sqlalchemy.orm import Session

from engine.engine import ScriptEngine
from db_setup import get_db
from services import preset_service, execution_service

router = APIRouter()
engine = ScriptEngine()


class RunRequest(BaseModel):
    preset_id: int


def _preset_to_engine_dict(preset) -> dict:
    """将数据库 Preset 转为引擎期望的字典格式"""
    flow = {}
    try:
        flow = json.loads(preset.flow_data) if preset.flow_data else {}
    except json.JSONDecodeError:
        flow = {}
    # 引擎期望: name, game, steps, max_runs, round_interval, chain
    return {
        "name": preset.name,
        "game": getattr(preset, "game_name", ""),
        "steps": flow.get("steps", []),
        "max_runs": flow.get("max_runs", 0),
        "round_interval": flow.get("round_interval", 0),
        "chain": flow.get("chain", True),
        "preset_id": preset.id,
    }


@router.post("/run")
def start_run(req: RunRequest, db: Session = Depends(get_db)):
    """启动预设执行"""
    preset = preset_service.get_preset_by_id(db, req.preset_id)
    if not preset:
        raise HTTPException(404, f"预设不存在: id={req.preset_id}")

    preset_dict = _preset_to_engine_dict(preset)

    # 创建执行记录
    execution = execution_service.create_execution(db, req.preset_id, "running")

    def _run():
        try:
            engine.run(preset_dict, chain=True)
            execution_service.update_execution_status(db, execution.id, "completed")
        except Exception as e:
            execution_service.update_execution_status(
                db, execution.id, "error", error_message=str(e)
            )

    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()

    return {
        "status": "ok",
        "message": f"已启动: {preset.name}",
        "execution_id": execution.id,
    }


@router.post("/stop")
def stop_run():
    """停止执行"""
    engine.stop()
    return {"status": "ok", "message": "已停止"}


@router.get("/status")
def get_status():
    """获取引擎运行状态"""
    return engine.monitor()


# ══ 执行记录查询 ═══════════════════════════════

@router.get("/executions")
def list_executions(limit: int = 20, db: Session = Depends(get_db)):
    """获取最近的执行记录"""
    records = execution_service.get_recent_executions(db, limit)
    return [
        {
            "id": r.id,
            "preset_id": r.preset_id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/executions/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """获取单条执行记录及其步骤"""
    record = execution_service.get_execution(db, execution_id)
    if record is None:
        raise HTTPException(404, f"执行记录不存在: id={execution_id}")
    steps = execution_service.get_steps_by_execution(db, execution_id)
    return {
        "id": record.id,
        "preset_id": record.preset_id,
        "status": record.status,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        "duration_ms": record.duration_ms,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "steps": [
            {
                "id": s.id,
                "step_order": s.step_order,
                "node_id": s.node_id,
                "node_type": s.node_type,
                "status": s.status,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            }
            for s in steps
        ],
    }
