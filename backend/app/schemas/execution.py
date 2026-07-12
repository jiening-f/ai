"""
执行记录 Schema（请求/响应验证）
"""

from pydantic import BaseModel, Field


class ExecutionOut(BaseModel):
    """执行记录响应"""
    id: int
    preset_id: int | None
    status: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ExecutionStepOut(BaseModel):
    """执行步骤响应"""
    id: int
    execution_id: int
    step_order: int
    node_id: str
    node_type: str
    status: str
    input_data: str | None
    output_data: str | None
    started_at: str
    finished_at: str | None

    model_config = {"from_attributes": True}


class ExecutionDetailOut(ExecutionOut):
    """执行记录详情（含步骤）"""
    steps: list[ExecutionStepOut] = []

    model_config = {"from_attributes": True}
