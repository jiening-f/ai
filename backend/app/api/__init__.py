"""API 公共工具 — 统一响应格式、快捷查询"""
from typing import Any, Type
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def success(data: Any = None) -> dict:
    """统一成功响应"""
    return {"success": True, "data": data, "error": None}


def api_error(msg: str, code: int = 400) -> HTTPException:
    """统一错误响应"""
    return HTTPException(
        status_code=code,
        detail={"success": False, "data": None, "error": msg},
    )


async def get_or_404(model: Type, obj_id: int, db: AsyncSession):
    """按 ID 查询，不存在时 raise 404"""
    result = await db.execute(select(model).where(model.id == obj_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise api_error(f"{model.__tablename__} id={obj_id} 不存在", 404)
    return obj
