"""预设 Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PresetCreate(BaseModel):
    game_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    flow_data: str = Field(default="{}")
    is_active: bool = Field(default=False)


class PresetUpdate(BaseModel):
    game_id: Optional[int] = Field(None, gt=0)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    flow_data: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class PresetResponse(BaseModel):
    id: int
    game_id: int
    name: str
    description: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PresetDetailResponse(PresetResponse):
    flow_data: str = "{}"
