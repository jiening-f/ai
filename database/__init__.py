"""数据库 ORM 模型包 — 统一导出

所有模型和 Base 均定义在 database/models.py 中。
此包作为唯一的导入入口，避免多个 DeclarativeBase 实例。

用法:
    from database import Base, Game, Preset, Execution, ExecutionStep, Plugin, Setting
"""

from database.models import (
    Base,
    Game,
    Preset,
    Execution,
    ExecutionStep,
    Plugin,
    Setting,
)

__all__ = [
    "Base",
    "Game",
    "Preset",
    "Execution",
    "ExecutionStep",
    "Plugin",
    "Setting",
]
