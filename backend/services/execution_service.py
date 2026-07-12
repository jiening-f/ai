"""执行记录服务 — 执行记录和步骤日志的 CRUD"""

from datetime import datetime
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Execution, ExecutionStep


class ExecutionService:
    """执行记录管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_executions(
        self, preset_id: int | None = None, limit: int = 50
    ) -> list[Execution]:
        """获取执行记录列表，可按预设筛选"""
        stmt = select(Execution).order_by(Execution.started_at.desc()).limit(limit)
        if preset_id is not None:
            stmt = stmt.where(Execution.preset_id == preset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_execution(self, execution_id: int) -> Execution | None:
        """获取单个执行记录"""
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def create_execution(self, data: dict) -> Execution:
        """创建执行记录"""
        execution = Execution(**data)
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def update_execution(self, execution_id: int, data: dict) -> Execution | None:
        """更新执行记录（状态、结束时间、错误信息等）"""
        execution = await self.get_execution(execution_id)
        if execution is None:
            return None
        for key, value in data.items():
            if hasattr(execution, key):
                setattr(execution, key, value)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def finish_execution(
        self, execution_id: int, status: str, error_message: str | None = None
    ):
        """标记执行结束"""
        now = datetime.utcnow()
        execution = await self.get_execution(execution_id)
        if execution:
            execution.status = status
            execution.finished_at = now
            if error_message:
                execution.error_message = error_message
            if execution.started_at:
                execution.duration_ms = int(
                    (now - execution.started_at).total_seconds() * 1000
                )
            await self.db.flush()

    async def delete_execution(self, execution_id: int) -> bool:
        """删除执行记录（级联删除步骤日志）"""
        result = await self.db.execute(
            delete(Execution).where(Execution.id == execution_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ── 步骤日志 ──

    async def list_steps(self, execution_id: int) -> list[ExecutionStep]:
        """获取执行的步骤日志列表"""
        result = await self.db.execute(
            select(ExecutionStep)
            .where(ExecutionStep.execution_id == execution_id)
            .order_by(ExecutionStep.step_order)
        )
        return list(result.scalars().all())

    async def add_step(self, data: dict) -> ExecutionStep:
        """添加步骤日志"""
        step = ExecutionStep(**data)
        self.db.add(step)
        await self.db.flush()
        return step

    async def get_execution_count(self, preset_id: int | None = None) -> int:
        """获取执行记录总数"""
        stmt = select(func.count(Execution.id))
        if preset_id is not None:
            stmt = stmt.where(Execution.preset_id == preset_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
