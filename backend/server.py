"""
Uvicorn 启动脚本

用法：cd backend && python server.py
"""

import sys
import os

# 将项目根目录加入 Python 路径，确保可导入 database/ 等顶层模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
