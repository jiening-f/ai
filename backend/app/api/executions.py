"""
执行记录 API 路由

- GET /api/executions?preset_id={id}&limit=50 — 列表
- GET /api/executions/{id} — 详情（含步骤）
- GET /api/executions/{id}/steps — 步骤日志
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.execution import Execution, ExecutionStep
from app.schemas.game import ApiResponse

router = APIRouter(tags=["执行记录"])


@router.get("/executions", response_model=ApiResponse)
async def list_executions(
    preset_id: int = Query(default=None, description="按预设筛选"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取执行记录列表"""
    stmt = select(Execution)
    if preset_id:
        stmt = stmt.where(Execution.preset_id == preset_id)
    stmt = stmt.order_by(Execution.started_at.desc()).limit(limit)

    result = await db.execute(stmt)
    executions = result.scalars().all()

    return ApiResponse(success=True, data=[
        {
            "id": e.id, "preset_id": e.preset_id,
            "status": e.status,
            "started_at": str(e.started_at),
            "finished_at": str(e.finished_at) if e.finished_at else None,
            "duration_ms": e.duration_ms,
            "error_message": e.error_message,
        }
        for e in executions
    ])


@router.get("/executions/{execution_id}", response_model=ApiResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    """获取执行记录详情（含步骤日志）"""
    stmt = (
        select(Execution)
        .where(Execution.id == execution_id)
        .options(selectinload(Execution.steps))
    )
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return ApiResponse(success=True, data={
        "id": execution.id,
        "preset_id": execution.preset_id,
        "status": execution.status,
        "started_at": str(execution.started_at),
        "finished_at": str(execution.finished_at) if execution.finished_at else None,
        "duration_ms": execution.duration_ms,
        "error_message": execution.error_message,
        "steps": [
            {
                "id": s.id, "step_order": s.step_order,
                "node_id": s.node_id, "node_type": s.node_type,
                "status": s.status,
                "input_data": s.input_data, "output_data": s.output_data,
                "started_at": str(s.started_at),
                "finished_at": str(s.finished_at) if s.finished_at else None,
            }
            for s in sorted(execution.steps, key=lambda x: x.step_order)
        ],
    })


@router.get("/executions/{execution_id}/steps", response_model=ApiResponse)
async def list_execution_steps(execution_id: int, db: AsyncSession = Depends(get_db)):
    """获取执行步骤日志列表"""
    stmt = (
        select(ExecutionStep)
        .where(ExecutionStep.execution_id == execution_id)
        .order_by(ExecutionStep.step_order)
    )
    result = await db.execute(stmt)
    steps = result.scalars().all()

    return ApiResponse(success=True, data=[
        {
            "id": s.id, "execution_id": s.execution_id,
            "step_order": s.step_order,
            "node_id": s.node_id, "node_type": s.node_type,
            "status": s.status,
            "input_data": s.input_data, "output_data": s.output_data,
            "started_at": str(s.started_at),
            "finished_at": str(s.finished_at) if s.finished_at else None,
        }
        for s in steps
    ])
