"""
插件 Schema（请求/响应验证）
"""

from pydantic import BaseModel, Field


class PluginCreate(BaseModel):
    """安装插件请求"""
    name: str = Field(..., min_length=1, max_length=100, description="插件名称")
    version: str = Field(default="1.0.0", max_length=20, description="版本号")
    author: str = Field(default="", max_length=100, description="作者")
    description: str = Field(default="", max_length=500, description="描述")
    file_path: str = Field(default="", max_length=500, description="文件路径")


class PluginUpdate(BaseModel):
    """更新插件请求"""
    name: str | None = Field(None, max_length=100)
    enabled: bool | None = Field(None, description="启用/禁用")


class PluginOut(BaseModel):
    """插件响应"""
    id: int
    name: str
    version: str
    author: str
    description: str
    file_path: str
    enabled: bool
    installed_at: str

    model_config = {"from_attributes": True}
