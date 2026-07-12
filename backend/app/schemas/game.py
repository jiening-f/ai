"""
游戏 Schema（请求/响应验证）
"""

from pydantic import BaseModel, Field


class GameCreate(BaseModel):
    """创建游戏请求"""
    name: str = Field(..., min_length=1, max_length=100, description="游戏名称")
    window_title: str = Field(default="", max_length=200, description="窗口标题（模糊匹配）")
    window_class: str = Field(default="", max_length=200, description="窗口类名（精确匹配）")


class GameUpdate(BaseModel):
    """更新游戏请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    window_title: str | None = Field(None, max_length=200)
    window_class: str | None = Field(None, max_length=200)


class GameOut(BaseModel):
    """游戏响应"""
    id: int
    name: str
    window_title: str
    window_class: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool = True
    data: object = None
    error: str | None = None
