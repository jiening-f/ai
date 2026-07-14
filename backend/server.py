"""全能脚本 API 入口 — 端口 8765"""
import os, sys

# 路径引导：确保 backend/ 在 sys.path 中，使模块级导入在任意调用方式下均有效
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.db import init_db
from backend.engine.process_manager import shutdown_all, list_engines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化数据库
    await init_db()
    yield
    # 关闭时：清理所有引擎子进程
    shutdown_all()


app = FastAPI(title="全能脚本 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# 健康检查端点（Docker healthcheck 用）
@app.get("/api/health")
async def health():
    engines = list_engines()
    return {
        "status": "ok",
        "engine_count": len(engines),
        "engines": [
            {
                "execution_id": e["execution_id"],
                "mode": e["mode"],
                "status": e["status"],
            }
            for e in engines
        ],
    }


# 活跃引擎列表（管理员用）
@app.get("/api/engines")
async def get_engines():
    return {
        "engines": list_engines(),
    }


# ── Stage 2: 数据库驱动的 REST API（新架构）──
from app.api.games import router as games_router
from app.api.presets import router as presets_router
from app.api.executions import router as executions_router
from app.api.plugins import router as plugins_router
from app.api.settings import router as settings_router
from app.api.websocket import router as ws_router

app.include_router(games_router, prefix="/api")
app.include_router(presets_router, prefix="/api")
app.include_router(executions_router, prefix="/api")
app.include_router(plugins_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(ws_router)

# ── Stage 1: 旧版文件路由（兼容，挂载到 /api/legacy 避免冲突）──
from routes import presets as legacy_presets, run, nodes
app.include_router(legacy_presets.router, prefix="/api/legacy")
app.include_router(run.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")


if __name__ == "__main__":
    print("服务启动: http://127.0.0.1:8765")
    print("API 文档: http://127.0.0.1:8765/docs")
    uvicorn.run(app, host="127.0.0.1", port=8765)
