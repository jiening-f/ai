"""
预设 Schema（请求/响应验证）
"""

from pydantic import BaseModel, Field


class PresetCreate(BaseModel):
    """创建预设请求"""
    game_id: int = Field(..., description="所属游戏 ID")
    name: str = Field(..., min_length=1, max_length=100, description="预设名称")
    description: str = Field(default="", max_length=500, description="描述")
    flow_data: str = Field(default="{}", description="节点流程数据 JSON 字符串")
    is_active: bool = Field(default=False, description="是否启用")


class PresetUpdate(BaseModel):
    """更新预设请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    flow_data: str | None = None
    is_active: bool | None = None


class PresetOut(BaseModel):
    """预设响应"""
    id: int
    game_id: int
    name: str
    description: str
    flow_data: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PresetListOut(BaseModel):
    """预设列表项"""
    id: int
    game_id: int
    name: str
    description: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
