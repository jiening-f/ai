"""系统设置服务 — 设置的读写操作"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Setting


class SettingService:
    """系统设置管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> dict[str, str]:
        """获取所有设置（转为简单字典）"""
        result = await self.db.execute(select(Setting))
        return {s.key: s.value for s in result.scalars().all()}

    async def get(self, key: str) -> str | None:
        """获取单个设置值"""
        result = await self.db.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def set(self, key: str, value: str) -> Setting:
        """设置一个键值（upsert）"""
        result = await self.db.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            self.db.add(setting)
        await self.db.flush()
        await self.db.refresh(setting)
        return setting

    async def delete(self, key: str) -> bool:
        """删除一个设置"""
        result = await self.db.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            await self.db.delete(setting)
            await self.db.flush()
            return True
        return False

    async def get_many(self, keys: list[str]) -> dict[str, str]:
        """批量获取多个设置"""
        result = await self.db.execute(
            select(Setting).where(Setting.key.in_(keys))
        )
        return {s.key: s.value for s in result.scalars().all()}
