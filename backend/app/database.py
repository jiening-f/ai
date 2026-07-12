"""SQLAlchemy 异步引擎与会话管理

使用 SQLite + aiosqlite 作为本地数据库。
Base 类统一从 database.models 导入，确保只有一个 DeclarativeBase 实例。
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from database.models import Base  # 统一 Base 类
# 注册所有 ORM 模型（必须导入以触发映射注册）
import database.models  # noqa: F401

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
    """初始化数据库：建表 + 种子数据

    在应用启动时（lifespan）调用。
    """
    # 确保数据目录存在
    db_dir = os.path.dirname(settings.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 植入默认设置（如果 settings 表为空）
    await seed_default_settings()


async def seed_default_settings():
    """植入默认系统设置"""
    from database.models import Setting
    from sqlalchemy import select

    defaults = {
        "language": "zh-CN",
        "theme": "auto",
        "max_concurrent": "1",
        "log_level": "INFO",
        "screenshot_quality": "90",
        "ocr_engine": "windows",
        "default_timeout": "30000",
        "retry_count": "3",
        "retry_delay": "1000",
        "auto_screenshot": "true",
        "anti_detect_enabled": "true",
        "mouse_speed": "1.0",
        "keyboard_delay": "50",
        "template_threshold": "0.85",
        "max_screenshots_cache": "100",
    }

    async with async_session_factory() as session:
        result = await session.execute(select(Setting.key).limit(1))
        if result.first() is not None:
            return  # 已有数据，跳过

        for key, value in defaults.items():
            session.add(Setting(key=key, value=value))
        await session.commit()
