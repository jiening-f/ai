"""
设置 Schema（请求/响应验证）
"""

from pydantic import BaseModel, Field


class SettingUpdate(BaseModel):
    """更新设置请求"""
    value: str = Field(..., description="设置值")


class SettingOut(BaseModel):
    """设置响应"""
    key: str
    value: str
    updated_at: str

    model_config = {"from_attributes": True}
