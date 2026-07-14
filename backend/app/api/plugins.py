"""Plugins 插件管理 API — 列表/安装/启用禁用/卸载"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from database.models import Plugin
from app.schemas.plugin import PluginCreate, PluginUpdate, PluginResponse
from app.api import success, api_error, get_or_404

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("")
async def list_plugins(db: AsyncSession = Depends(get_db)):
    """插件列表"""
    result = await db.execute(select(Plugin).order_by(Plugin.installed_at.desc()))
    return success([PluginResponse.model_validate(p).model_dump(mode="json")
                     for p in result.scalars().all()])


@router.post("", status_code=201)
async def install_plugin(body: PluginCreate, db: AsyncSession = Depends(get_db)):
    """安装插件 — 同名返回 409"""
    plugin = Plugin(name=body.name, version=body.version, author=body.author,
                    description=body.description, file_path=body.file_path)
    db.add(plugin)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise api_error(f"插件 «{body.name}» 已存在", 409)

    await db.refresh(plugin)
    return success(PluginResponse.model_validate(plugin).model_dump(mode="json"))


@router.put("/{plugin_id}")
async def toggle_plugin(plugin_id: int, body: PluginUpdate, db: AsyncSession = Depends(get_db)):
    """启用/禁用插件"""
    plugin = await get_or_404(Plugin, plugin_id, db)
    plugin.enabled = body.enabled
    plugin.updated_at = datetime.now()
    await db.flush()
    await db.refresh(plugin)
    return success(PluginResponse.model_validate(plugin).model_dump(mode="json"))


@router.delete("/{plugin_id}")
async def uninstall_plugin(plugin_id: int, db: AsyncSession = Depends(get_db)):
    """卸载插件"""
    plugin = await get_or_404(Plugin, plugin_id, db)
    await db.delete(plugin)
    await db.flush()
    return success({"uninstalled": True, "id": plugin_id})
