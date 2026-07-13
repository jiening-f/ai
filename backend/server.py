"""全能脚本 API 入口 — 端口 8765"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动创建数据库表"""
    await init_db()
    yield


app = FastAPI(title="全能脚本 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 健康检查端点（Docker healthcheck 用）
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# ── Stage 2: 数据库驱动的 REST API（新架构）──
from app.api.games import router as games_router
from app.api.presets import router as presets_router
from app.api.executions import router as executions_router
from app.api.plugins import router as plugins_router
from app.api.settings import router as settings_router
from app.api.websocket import router as ws_router
from app.api.logs import router as logs_router

app.include_router(games_router, prefix="/api")
app.include_router(presets_router, prefix="/api")
app.include_router(executions_router, prefix="/api")
app.include_router(plugins_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(ws_router)
app.include_router(logs_router, prefix="/api")

# ── Stage 1: 旧版文件路由（兼容，挂载到 /api/legacy 避免冲突）──
from routes import presets as legacy_presets, run, nodes
app.include_router(legacy_presets.router, prefix="/api/legacy")
app.include_router(run.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")


if __name__ == "__main__":
    print("服务启动: http://127.0.0.1:8765")
    print("API 文档: http://127.0.0.1:8765/docs")
    uvicorn.run(app, host="127.0.0.1", port=8765)
