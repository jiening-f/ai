"""
游戏配置 ORM 模型
"""

import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="游戏名称")
    window_title: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="窗口标题（模糊匹配）")
    window_class: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="窗口类名（精确匹配）")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
