"""Settings 系统设置 API — 获取全部/更新单个"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from database.models import Setting
from app.schemas.setting import SettingUpdate, SettingResponse
from app.api import success

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
async def list_settings(db: AsyncSession = Depends(get_db)):
    """获取所有设置"""
    result = await db.execute(select(Setting).order_by(Setting.key))
    return success([SettingResponse.model_validate(s).model_dump(mode="json")
                     for s in result.scalars().all()])


@router.put("/{key}")
async def update_setting(key: str, body: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新设置（不存在则创建）"""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    now = datetime.now()
    if setting:
        setting.value = body.value
        setting.updated_at = now
    else:
        setting = Setting(key=key, value=body.value, updated_at=now)
        db.add(setting)

    await db.flush()
    await db.refresh(setting)
    return success(SettingResponse.model_validate(setting).model_dump(mode="json"))
