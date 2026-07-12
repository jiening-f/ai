"""预设 API — 对接数据库 Service 层"""

import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db_setup import get_db
from services import preset_service

router = APIRouter()


# ══ 序列化辅助 ═════════════════════════════════

def _preset_to_dict(preset) -> dict:
    """将 ORM 对象转为前端友好的字典"""
    flow = {}
    try:
        flow = json.loads(preset.flow_data) if preset.flow_data else {}
    except json.JSONDecodeError:
        flow = {}
    return {
        "id": preset.id,
        "game_id": preset.game_id,
        "name": preset.name,
        "description": preset.description,
        "flow_data": flow,
        "is_active": preset.is_active,
        "created_at": preset.created_at.isoformat() if preset.created_at else None,
        "updated_at": preset.updated_at.isoformat() if preset.updated_at else None,
    }


# ══ 请求模型 ═══════════════════════════════════

class PresetCreate(BaseModel):
    name: str
    game_id: int = 1
    description: str = ""
    flow_data: Optional[dict] = None


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    game_id: Optional[int] = None
    description: Optional[str] = None
    flow_data: Optional[dict] = None


# ══ 路由 ═══════════════════════════════════════

@router.get("/presets")
def list_presets(db: Session = Depends(get_db)):
    """获取所有预设"""
    presets = preset_service.get_all_presets(db)
    return [_preset_to_dict(p) for p in presets]


@router.get("/presets/active")
def get_active(db: Session = Depends(get_db)):
    """获取当前活跃的预设"""
    preset = preset_service.get_active_preset(db)
    if preset is None:
        raise HTTPException(404, "没有活跃的预设")
    return _preset_to_dict(preset)


@router.get("/presets/{preset_id}")
def get_preset_route(preset_id: int, db: Session = Depends(get_db)):
    """按 ID 获取预设"""
    preset = preset_service.get_preset_by_id(db, preset_id)
    if preset is None:
        raise HTTPException(404, f"预设不存在: id={preset_id}")
    return _preset_to_dict(preset)


@router.post("/presets", status_code=201)
def create_preset_route(data: PresetCreate, db: Session = Depends(get_db)):
    """创建新预设"""
    flow_str = json.dumps(data.flow_data, ensure_ascii=False) if data.flow_data else "{}"
    preset = preset_service.create_preset(
        db,
        name=data.name,
        game_id=data.game_id,
        description=data.description,
        flow_data=flow_str,
    )
    return _preset_to_dict(preset)


@router.put("/presets/{preset_id}")
def update_preset_route(preset_id: int, data: PresetUpdate, db: Session = Depends(get_db)):
    """更新预设"""
    kwargs = data.model_dump(exclude_none=True)
    if "flow_data" in kwargs and kwargs["flow_data"] is not None:
        kwargs["flow_data"] = json.dumps(kwargs["flow_data"], ensure_ascii=False)
    preset = preset_service.update_preset(db, preset_id, **kwargs)
    if preset is None:
        raise HTTPException(404, f"预设不存在: id={preset_id}")
    return _preset_to_dict(preset)


@router.delete("/presets/{preset_id}")
def delete_preset_route(preset_id: int, db: Session = Depends(get_db)):
    """删除预设"""
    ok = preset_service.delete_preset(db, preset_id)
    if not ok:
        raise HTTPException(404, f"预设不存在: id={preset_id}")
    return {"status": "ok"}


@router.post("/presets/{preset_id}/activate")
def activate_preset_route(preset_id: int, db: Session = Depends(get_db)):
    """设为活跃预设"""
    preset = preset_service.set_active_preset(db, preset_id)
    if preset is None:
        raise HTTPException(404, f"预设不存在: id={preset_id}")
    return _preset_to_dict(preset)
