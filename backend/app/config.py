"""
应用配置管理

使用 pydantic-settings 管理所有配置项，支持从环境变量读取。
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 应用
    app_name: str = "全能脚本工具"
    app_version: str = "0.1.0"
    debug: bool = False

    # 服务
    host: str = "127.0.0.1"
    port: int = 8765

    # 数据库（SQLite）—— 相对于 backend/ 目录
    db_path: str = "data/app.db"
    db_echo: bool = False  # 是否打印 SQL 日志

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",   # Vite 开发服务器
        "http://127.0.0.1:5173",
    ]

    @property
    def database_url(self) -> str:
        """生成 SQLAlchemy 异步连接 URL"""
        return f"sqlite+aiosqlite:///{self.db_path}"

    model_config = {
        "env_prefix": "APP_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# 全局单例
settings = Settings()

# 基于 config.py 自身位置解析绝对路径（不依赖 CWD）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/app/
_BACKEND_DIR = os.path.dirname(_THIS_DIR)                # backend/
DB_PATH = os.path.join(_BACKEND_DIR, settings.db_path)   # backend/data/app.db
DB_DIR = os.path.dirname(DB_PATH)                        # backend/data/
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
