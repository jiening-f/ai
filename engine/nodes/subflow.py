"""
子流程节点

- SubFlowNode: 调用另一个预设/脚本作为子流程执行
"""

from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class SubFlowNode(BaseNode):
    """调用子流程节点"""

    node_type = "sub_flow"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        sub_preset_id = self.config.get("sub_preset_id", 0)
        sub_flow_data = self.config.get("sub_flow_data", None)
        pass_variables = self.config.get("pass_variables", True)

        ctx.log(f"[子流程] 调用预设 {sub_preset_id}")

        if sub_flow_data:
            # 如果有内联的 flow_data，则直接执行
            ctx.log(f"[子流程] 使用内联流程数据")
            # 子流程的实际执行由执行器在外部处理
            ctx.set_var("sub_flow_data", sub_flow_data)
        elif sub_preset_id > 0:
            ctx.set_var("sub_preset_id", sub_preset_id)
        else:
            return NodeResult(success=False, error_message="子流程未指定预设 ID 或流程数据")

        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("sub_preset_id") or self.config.get("sub_flow_data"))

    @classmethod
    def default_config(cls) -> dict:
        return {"sub_preset_id": 0, "sub_flow_data": None, "pass_variables": True}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "子流程",
            "category": "流程控制",
            "description": "调用另一个预设或脚本作为子流程执行，完成后返回继续执行",
            "config_schema": {
                "sub_preset_id": {"type": "number", "default": 0, "description": "子预设 ID"},
                "sub_flow_data": {"type": "object", "default": None, "description": "内联流程数据"},
                "pass_variables": {"type": "boolean", "default": True, "description": "是否传递当前变量到子流程"},
            },
        }
