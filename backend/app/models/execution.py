"""
执行记录 ORM 模型
"""

import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[int] = mapped_column(Integer, ForeignKey("presets.id", ondelete="SET NULL"), nullable=True, comment="关联预设")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", comment="状态: running/paused/completed/stopped/error")
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="执行耗时(毫秒)")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # 关联
    preset: Mapped["Preset | None"] = relationship("Preset", lazy="selectin")  # noqa: F821
    steps: Mapped[list["ExecutionStep"]] = relationship("ExecutionStep", lazy="selectin", back_populates="execution")  # noqa: F821


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, comment="所属执行")
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="执行序号")
    node_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="节点 ID")
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="节点类型")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", comment="步骤状态")
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="输入数据 JSON")
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="输出数据 JSON")
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联
    execution: Mapped["Execution"] = relationship("Execution", lazy="selectin", back_populates="steps")  # noqa: F821
