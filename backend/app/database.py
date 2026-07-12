"""
SQLAlchemy 异步引擎与会话管理

使用 SQLite + aiosqlite 作为本地数据库。
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from app.models.base import Base
import app.models.game     # noqa: F401 — 注册 ORM 模型
import app.models.preset   # noqa: F401
import app.models.execution  # noqa: F401
import app.models.plugin   # noqa: F401
import app.models.setting  # noqa: F401

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
)

# 异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库

    确保数据目录存在，并创建所有表。
    在应用启动时调用。
    """
    # 确保数据目录存在
    db_dir = os.path.dirname(settings.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
