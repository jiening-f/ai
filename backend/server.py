from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import sys


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化引擎管理器
    from engine.process_manager import manager as pm
    app.state.process_manager = pm
    print("  ProcessManager 已就绪")
    yield
    # 关闭时：清理所有引擎进程
    print("  正在关闭所有引擎进程...")
    pm.stop_all(timeout=3)
    print("  所有引擎进程已清理")


app = FastAPI(title="全能脚本 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 健康检查端点（Docker healthcheck 用）
@app.get("/api/health")
async def health():
    from engine.process_manager import manager as pm
    return {"status": "ok", "engines": pm.list_engines()}

# 注册路由
from routes import presets, run, nodes
app.include_router(presets.router, prefix="/api")
app.include_router(run.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")

# 引擎管理端点
from engine.process_manager import manager as pm

@app.get("/api/engines")
async def list_engines():
    return pm.list_engines()

# ── 前端静态文件服务（SPA） ──
def _find_static_dir():
    """查找前端静态文件目录（支持 PyInstaller 打包和开发模式）"""
    # PyInstaller 打包后资源在 _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
        candidates = [
            os.path.join(base, "static"),
        ]
        for p in candidates:
            if os.path.isdir(p):
                return p
    # 开发模式
    base = os.path.dirname(os.path.abspath(__file__))
    for p in [
        os.path.join(base, "static"),
        os.path.join(os.path.dirname(base), "frontend", "dist"),
    ]:
        if os.path.isdir(p):
            return p
    return None

static_dir = _find_static_dir()
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    print(f"  静态文件目录: {static_dir}")

if __name__ == "__main__":
    print("服务启动: http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765)
