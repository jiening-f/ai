"""全能脚本 API 服务入口"""

import sys
import os

# 确保项目根目录在 sys.path 中，使 database 模块可导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from db_setup import init_db, seed_default_settings


# ─── 生命周期 ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建数据库表并植入默认设置"""
    init_db()
    seed_default_settings()
    yield


app = FastAPI(title="全能脚本 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 注册路由
from routes import presets, run, nodes
app.include_router(presets.router, prefix="/api")
app.include_router(run.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")

if __name__ == "__main__":
    print("服务启动: http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765)
