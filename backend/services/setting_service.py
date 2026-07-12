"""系统设置 Service — CRUD"""

from typing import Optional, Dict
from sqlalchemy.orm import Session
from database.models import Setting


def get_all_settings(db: Session) -> Dict[str, str]:
    """获取所有设置，返回 {key: value} 字典"""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


def get_setting(db: Session, key: str) -> Optional[str]:
    """获取单个设置值"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else None


def set_setting(db: Session, key: str, value: str) -> Setting:
    """设置/更新一个配置项（upsert）"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def batch_set_settings(db: Session, items: Dict[str, str]) -> int:
    """批量设置配置项，返回更新数量"""
    count = 0
    for key, value in items.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.add(setting)
        count += 1
    db.commit()
    return count


def delete_setting(db: Session, key: str) -> bool:
    """删除一个配置项"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting is None:
        return False
    db.delete(setting)
    db.commit()
    return True
