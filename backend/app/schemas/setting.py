"""系统设置 Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
