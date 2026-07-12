"""
数据操作节点

- VariableSetNode: 变量赋值
- TextOutputNode: 文本输出（用于调试/日志）
"""

from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class VariableSetNode(BaseNode):
    """变量赋值节点"""

    node_type = "variable_set"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        var_name = self.config.get("var_name", "")
        var_value = self.config.get("var_value", "")

        if not var_name:
            return NodeResult(success=False, error_message="未指定变量名")

        ctx.set_var(var_name, var_value)
        ctx.log(f"[变量] {var_name} = {var_value}")
        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("var_name"))

    @classmethod
    def default_config(cls) -> dict:
        return {"var_name": "", "var_value": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "变量赋值",
            "category": "数据",
            "description": "设置一个变量的值，可在后续节点中通过条件判断或 $变量名 引用",
            "config_schema": {
                "var_name": {"type": "string", "default": "", "description": "变量名"},
                "var_value": {"type": "string", "default": "", "description": "变量值"},
            },
        }


class TextOutputNode(BaseNode):
    """文本输出节点（调试日志）"""

    node_type = "text_output"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        text = self.config.get("text", "")
        # 支持变量替换: $var_name → 实际值
        import re
        def replace_var(match):
            var_name = match.group(1)
            return str(ctx.get_var(var_name, ""))
        text = re.sub(r'\$(\w+)', replace_var, text)

        ctx.log(f"[输出] {text}")
        ctx.set_var("last_output", text)
        return NodeResult(success=True, data={"text": text})

    @classmethod
    def default_config(cls) -> dict:
        return {"text": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "文本输出",
            "category": "数据",
            "description": "输出日志文本，支持 $变量名 引用变量值",
            "config_schema": {
                "text": {"type": "string", "default": "", "description": "输出文本，支持 $变量名"},
            },
        }
