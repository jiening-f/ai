from fastapi import APIRouter, HTTPException
from core.config import get_presets, get_preset, save_preset, del_preset

router = APIRouter()

@router.get("/presets")
def list_presets():
    return get_presets()

@router.get("/presets/{name}")
def get_preset_route(name: str):
    result = get_preset(name)
    if result is None:
        raise HTTPException(404, f"预设不存在: {name}")
    return result

@router.post("/presets")
def save_preset_route(data: dict):
    save_preset(data)
    return {"status": "ok"}

@router.delete("/presets/{name}")
def delete_preset_route(name: str):
    del_preset(name)
    return {"status": "ok"}
