"""
预设配置 ORM 模型
"""

import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Preset(Base):
    __tablename__ = "presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, comment="所属游戏")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="预设名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="描述")
    flow_data: Mapped[str] = mapped_column(Text, nullable=False, default="{}", comment="节点流程数据 JSON")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否启用")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    game: Mapped["Game"] = relationship("Game", lazy="selectin")  # noqa: F821
