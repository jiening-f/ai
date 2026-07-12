"""预设 Service — CRUD + 活跃预设管理"""

from typing import Optional, List
from sqlalchemy.orm import Session
from database.models import Preset


def get_all_presets(db: Session) -> List[Preset]:
    """获取所有预设，按更新时间倒序"""
    return db.query(Preset).order_by(Preset.updated_at.desc()).all()


def get_preset_by_id(db: Session, preset_id: int) -> Optional[Preset]:
    """按 ID 获取预设"""
    return db.query(Preset).filter(Preset.id == preset_id).first()


def get_active_preset(db: Session) -> Optional[Preset]:
    """获取当前活跃的预设"""
    return db.query(Preset).filter(Preset.is_active == True).first()


def create_preset(db: Session, name: str, game_id: int = 1,
                  description: str = "", flow_data: str = "{}") -> Preset:
    """创建新预设"""
    preset = Preset(
        game_id=game_id,
        name=name,
        description=description,
        flow_data=flow_data,
        is_active=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


def update_preset(db: Session, preset_id: int, **kwargs) -> Optional[Preset]:
    """更新预设字段"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if preset is None:
        return None
    allowed = {"name", "description", "flow_data", "game_id"}
    for k, v in kwargs.items():
        if k in allowed and hasattr(preset, k):
            setattr(preset, k, v)
    db.commit()
    db.refresh(preset)
    return preset


def delete_preset(db: Session, preset_id: int) -> bool:
    """删除预设"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if preset is None:
        return False
    db.delete(preset)
    db.commit()
    return True


def set_active_preset(db: Session, preset_id: int) -> Optional[Preset]:
    """将一个预设设为活跃，其余取消活跃"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if preset is None:
        return None
    # 取消所有活跃
    db.query(Preset).filter(Preset.is_active == True).update({"is_active": False})
    # 激活目标
    preset.is_active = True
    db.commit()
    db.refresh(preset)
    return preset
