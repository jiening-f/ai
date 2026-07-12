"""Executions 执行记录 API — 列表/详情/步骤日志"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db
from database.models import Execution, ExecutionStep
from app.schemas.execution import (
    ExecutionResponse, ExecutionDetailResponse, ExecutionStepResponse,
)
from app.api import success, get_or_404

router = APIRouter(prefix="/executions", tags=["Executions"])


@router.get("")
async def list_executions(
    preset_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """执行记录列表，按创建时间倒序"""
    stmt = select(Execution)
    if preset_id is not None:
        stmt = stmt.where(Execution.preset_id == preset_id)
    stmt = stmt.order_by(Execution.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return success([ExecutionResponse.model_validate(e).model_dump(mode="json")
                     for e in result.scalars().all()])


@router.get("/{execution_id}")
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    """执行记录详情（含步骤日志）"""
    result = await db.execute(
        select(Execution)
        .where(Execution.id == execution_id)
        .options(selectinload(Execution.steps))
    )
    ex = result.scalar_one_or_none()
    if ex is None:
        from app.api import api_error
        raise api_error(f"执行记录 id={execution_id} 不存在", 404)

    detail = ExecutionDetailResponse.model_validate(ex).model_dump(mode="json")
    detail["steps"] = [
        ExecutionStepResponse.model_validate(s).model_dump(mode="json")
        for s in sorted(ex.steps, key=lambda s: s.step_order)
    ]
    return success(detail)


@router.get("/{execution_id}/steps")
async def list_steps(execution_id: int, db: AsyncSession = Depends(get_db)):
    """获取某次执行的分步日志"""
    await get_or_404(Execution, execution_id, db)
    result = await db.execute(
        select(ExecutionStep)
        .where(ExecutionStep.execution_id == execution_id)
        .order_by(ExecutionStep.step_order)
    )
    return success([ExecutionStepResponse.model_validate(s).model_dump(mode="json")
                     for s in result.scalars().all()])
