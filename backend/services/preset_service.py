"""预设服务 — 预设的 CRUD 和执行控制"""

from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Preset, Execution


class PresetService:
    """预设管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_presets(self, game_id: int | None = None) -> list[Preset]:
        """获取预设列表，可按游戏筛选"""
        stmt = select(Preset)
        if game_id is not None:
            stmt = stmt.where(Preset.game_id == game_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_preset(self, preset_id: int) -> Preset | None:
        """获取单个预设"""
        result = await self.db.execute(
            select(Preset).where(Preset.id == preset_id)
        )
        return result.scalar_one_or_none()

    async def create_preset(self, data: dict) -> Preset:
        """创建预设"""
        preset = Preset(**data)
        self.db.add(preset)
        await self.db.flush()
        await self.db.refresh(preset)
        return preset

    async def update_preset(self, preset_id: int, data: dict) -> Preset | None:
        """更新预设"""
        preset = await self.get_preset(preset_id)
        if preset is None:
            return None
        for key, value in data.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        await self.db.flush()
        await self.db.refresh(preset)
        return preset

    async def delete_preset(self, preset_id: int) -> bool:
        """删除预设（级联删除关联的执行记录）"""
        result = await self.db.execute(
            delete(Preset).where(Preset.id == preset_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def set_active(self, preset_id: int, active: bool = True):
        """设置预设的启用状态"""
        preset = await self.get_preset(preset_id)
        if preset:
            preset.is_active = active
            await self.db.flush()

    async def get_active_presets(self, game_id: int | None = None) -> list[Preset]:
        """获取所有启用的预设"""
        stmt = select(Preset).where(Preset.is_active == True)  # noqa: E712
        if game_id is not None:
            stmt = stmt.where(Preset.game_id == game_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
