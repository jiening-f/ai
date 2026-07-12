"""数据库引擎 & Session 管理

提供:
    - SQLite 引擎（项目根目录 data/app.db）
    - Session 工厂
    - init_db() — 启动时建表
    - seed_default_settings() — 默认设置种子数据
    - get_db() — FastAPI 依赖注入
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# ─── 路径 ──────────────────────────────────────
# db_setup.py 位于 backend/ 目录，项目根 = os.path.dirname(BASE_DIR)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

# ─── 引擎 & Session ────────────────────────────
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # SQLite 允许跨线程访问
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ─── 默认设置种子数据（来自 database/seeds/default_settings.sql）──
DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "zh-CN",
    "backend_port": "8765",
    "log_level": "INFO",
    "screenshot_quality": "90",
    "screenshot_format": "png",
    "ocr_language": "chi_sim",
    "ocr_engine": "auto",
    "template_match_threshold": "0.8",
    "input_delay_ms": "50",
    "mouse_speed": "0.5",
    "websocket_heartbeat_interval": "30",
    "max_execution_logs": "1000",
    "auto_save_interval_sec": "30",
    "plugin_auto_load": "true",
}


def init_db():
    """创建所有表（如果不存在）并从 database/models.py 导入 Base"""
    from database.models import Base  # 统一的 Base 实例
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def seed_default_settings():
    """写入默认设置 — INSERT OR IGNORE 语义"""
    from database.models import Setting
    db = SessionLocal()
    try:
        for key, value in DEFAULT_SETTINGS.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if existing is None:
                db.add(Setting(key=key, value=value))
        db.commit()
    finally:
        db.close()


def get_db():
    """FastAPI 依赖注入 — 每个请求一个 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
