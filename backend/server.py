#!/usr/bin/env python
"""
Uvicorn 启动脚本

用法：cd backend && python server.py
"""

import sys
import os

# 将 backend/ 目录加入 Python 路径最前面
_backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _backend_dir)

# 也将项目根加入路径（用于导入 database/ 等顶层模块）
_project_root = os.path.dirname(_backend_dir)
if _project_root not in sys.path:
    sys.path.insert(1, _project_root)  # 注意：插入到 pos 1，让 backend/ 的 engine 优先

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
