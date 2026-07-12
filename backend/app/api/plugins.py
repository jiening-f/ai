"""
插件管理 API 路由

- GET /api/plugins — 列表
- POST /api/plugins — 安装
- PUT /api/plugins/{id} — 启用/禁用
- DELETE /api/plugins/{id} — 卸载
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.plugin import Plugin
from app.schemas.plugin import PluginCreate, PluginUpdate
from app.schemas.game import ApiResponse

router = APIRouter(tags=["插件管理"])


@router.get("/plugins", response_model=ApiResponse)
async def list_plugins(db: AsyncSession = Depends(get_db)):
    """获取插件列表"""
    result = await db.execute(select(Plugin).order_by(Plugin.installed_at.desc()))
    plugins = result.scalars().all()

    return ApiResponse(success=True, data=[
        {
            "id": p.id, "name": p.name, "version": p.version,
            "author": p.author, "description": p.description,
            "file_path": p.file_path, "enabled": p.enabled,
            "installed_at": str(p.installed_at),
        }
        for p in plugins
    ])


@router.post("/plugins", response_model=ApiResponse, status_code=201)
async def create_plugin(body: PluginCreate, db: AsyncSession = Depends(get_db)):
    """安装插件"""
    plugin = Plugin(
        name=body.name, version=body.version, author=body.author,
        description=body.description, file_path=body.file_path,
    )
    db.add(plugin)
    await db.flush()
    await db.refresh(plugin)

    return ApiResponse(success=True, data={
        "id": plugin.id, "name": plugin.name, "version": plugin.version,
        "author": plugin.author, "description": plugin.description,
        "file_path": plugin.file_path, "enabled": plugin.enabled,
        "installed_at": str(plugin.installed_at),
    })


@router.put("/plugins/{plugin_id}", response_model=ApiResponse)
async def update_plugin(plugin_id: int, body: PluginUpdate, db: AsyncSession = Depends(get_db)):
    """更新插件（启用/禁用）"""
    result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="插件不存在")

    if body.name is not None:
        plugin.name = body.name
    if body.enabled is not None:
        plugin.enabled = body.enabled

    await db.flush()
    await db.refresh(plugin)

    return ApiResponse(success=True, data={
        "id": plugin.id, "name": plugin.name, "version": plugin.version,
        "author": plugin.author, "description": plugin.description,
        "file_path": plugin.file_path, "enabled": plugin.enabled,
        "installed_at": str(plugin.installed_at),
    })


@router.delete("/plugins/{plugin_id}", response_model=ApiResponse)
async def delete_plugin(plugin_id: int, db: AsyncSession = Depends(get_db)):
    """卸载插件"""
    result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="插件不存在")

    await db.delete(plugin)
    await db.flush()
    return ApiResponse(success=True, data={"deleted_id": plugin_id})
