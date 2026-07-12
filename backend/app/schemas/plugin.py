"""插件 Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PluginCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0.0", max_length=20)
    author: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=500)
    file_path: str = Field(default="", max_length=500)


class PluginUpdate(BaseModel):
    enabled: bool


class PluginResponse(BaseModel):
    id: int
    name: str
    version: str
    author: str
    description: str
    file_path: str
    enabled: bool
    installed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
