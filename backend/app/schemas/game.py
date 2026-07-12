"""游戏 Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GameCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    window_title: str = Field(default="", max_length=200)
    window_class: str = Field(default="", max_length=200)


class GameUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    window_title: Optional[str] = Field(None, max_length=200)
    window_class: Optional[str] = Field(None, max_length=200)


class GameResponse(BaseModel):
    id: int
    name: str
    window_title: str
    window_class: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
