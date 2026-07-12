"""执行记录 Service — CRUD + 步骤管理"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Execution, ExecutionStep


# ══ 执行记录 ═══════════════════════════════════

def create_execution(db: Session, preset_id: int, status: str = "pending") -> Execution:
    """创建新的执行记录"""
    execution = Execution(preset_id=preset_id, status=status)
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def get_execution(db: Session, execution_id: int) -> Optional[Execution]:
    """按 ID 获取执行记录"""
    return db.query(Execution).filter(Execution.id == execution_id).first()


def get_executions_by_preset(db: Session, preset_id: int) -> List[Execution]:
    """获取某个预设的所有执行记录"""
    return (
        db.query(Execution)
        .filter(Execution.preset_id == preset_id)
        .order_by(Execution.created_at.desc())
        .all()
    )


def get_recent_executions(db: Session, limit: int = 20) -> List[Execution]:
    """获取最近的执行记录"""
    return (
        db.query(Execution)
        .order_by(Execution.created_at.desc())
        .limit(limit)
        .all()
    )


def update_execution_status(
    db: Session,
    execution_id: int,
    status: str,
    error_message: Optional[str] = None,
) -> Optional[Execution]:
    """更新执行状态"""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if execution is None:
        return None
    execution.status = status
    if status == "running" and execution.started_at is None:
        execution.started_at = datetime.utcnow()
    if status in ("completed", "stopped", "error"):
        execution.finished_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_ms = int(
                (execution.finished_at - execution.started_at).total_seconds() * 1000
            )
    if error_message is not None:
        execution.error_message = error_message
    db.commit()
    db.refresh(execution)
    return execution


def delete_execution(db: Session, execution_id: int) -> bool:
    """删除执行记录"""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if execution is None:
        return False
    db.delete(execution)
    db.commit()
    return True


# ══ 执行步骤 ═══════════════════════════════════

def add_step(
    db: Session,
    execution_id: int,
    step_order: int,
    node_id: str = "",
    node_type: str = "",
    input_data: str = "{}",
    status: str = "pending",
) -> ExecutionStep:
    """添加执行步骤"""
    step = ExecutionStep(
        execution_id=execution_id,
        step_order=step_order,
        node_id=node_id,
        node_type=node_type,
        status=status,
        input_data=input_data,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def update_step_status(
    db: Session,
    step_id: int,
    status: str,
    output_data: Optional[str] = None,
) -> Optional[ExecutionStep]:
    """更新步骤状态"""
    step = db.query(ExecutionStep).filter(ExecutionStep.id == step_id).first()
    if step is None:
        return None
    step.status = status
    if status == "running" and step.started_at is None:
        step.started_at = datetime.utcnow()
    if status in ("completed", "error", "skipped"):
        step.finished_at = datetime.utcnow()
    if output_data is not None:
        step.output_data = output_data
    db.commit()
    db.refresh(step)
    return step


def get_steps_by_execution(db: Session, execution_id: int) -> List[ExecutionStep]:
    """获取某个执行记录的所有步骤"""
    return (
        db.query(ExecutionStep)
        .filter(ExecutionStep.execution_id == execution_id)
        .order_by(ExecutionStep.step_order)
        .all()
    )
