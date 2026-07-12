from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="全能脚本 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 注册路由
from routes import presets, run, nodes
app.include_router(presets.router, prefix="/api")
app.include_router(run.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")

if __name__ == "__main__":
    print("服务启动: http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765)
