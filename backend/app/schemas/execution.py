"""执行记录 Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExecutionResponse(BaseModel):
    id: int
    preset_id: int
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExecutionStepResponse(BaseModel):
    id: int
    execution_id: int
    step_order: int
    node_id: str
    node_type: str
    status: str
    input_data: str
    output_data: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExecutionDetailResponse(ExecutionResponse):
    steps: list[ExecutionStepResponse] = []
