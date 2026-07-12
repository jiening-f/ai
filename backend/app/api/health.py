"""
健康检查路由

GET /api/health → {"status": "ok"}
"""

from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check():
    """健康检查端点，返回服务运行状态"""
    return {"status": "ok"}
