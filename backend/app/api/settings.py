"""
系统设置 API 路由

- GET /api/settings — 所有设置
- PUT /api/settings/{key} — 更新单个设置
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingUpdate
from app.schemas.game import ApiResponse

router = APIRouter(tags=["系统设置"])


@router.get("/settings", response_model=ApiResponse)
async def list_settings(db: AsyncSession = Depends(get_db)):
    """获取所有设置"""
    result = await db.execute(select(Setting))
    settings = result.scalars().all()

    return ApiResponse(success=True, data=[
        {"key": s.key, "value": s.value, "updated_at": str(s.updated_at)}
        for s in settings
    ])


@router.put("/settings/{key}", response_model=ApiResponse)
async def update_setting(key: str, body: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新或创建单个设置"""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = body.value
    else:
        setting = Setting(key=key, value=body.value)
        db.add(setting)

    await db.flush()
    await db.refresh(setting)

    return ApiResponse(success=True, data={
        "key": setting.key, "value": setting.value, "updated_at": str(setting.updated_at),
    })
