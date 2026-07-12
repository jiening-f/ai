"""
插件 ORM 模型
"""

import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="插件名称")
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0", comment="版本号")
    author: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="作者")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="描述")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="文件路径")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    installed_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
