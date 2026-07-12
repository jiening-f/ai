"""
FastAPI 应用入口

创建应用实例、配置 CORS、注册路由、绑定生命周期事件。
"""

# 确保 backend/ 目录在 sys.path 最前面
# （与 server.py 配合：server.py 放 pos 0，project root 放 pos 1，
#  避免项目根 ai/engine/ 遮蔽 backend/engine/）
import sys
import os
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for i, p in enumerate(sys.path):
    if p in ('', _backend_root):
        sys.path.pop(i)
        break
sys.path.insert(0, _backend_root)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
from app.api.health import router as health_router  # noqa: E402
from app.api.games import router as games_router  # noqa: E402
from app.api.presets import router as presets_router  # noqa: E402
from app.api.executions import router as executions_router  # noqa: E402
from app.api.plugins import router as plugins_router  # noqa: E402
from app.api.settings import router as settings_router  # noqa: E402
from app.api.websocket import router as websocket_router  # noqa: E402

app.include_router(health_router, prefix="/api")
app.include_router(games_router, prefix="/api")
app.include_router(presets_router, prefix="/api")
app.include_router(executions_router, prefix="/api")
app.include_router(plugins_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
