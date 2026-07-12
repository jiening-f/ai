"""数据处理节点：variable_set, text_output。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class VariableSetNode(BaseNode):
    """变量赋值节点。"""
    node_type = "variable_set"
    node_category = "数据"
    node_description = "设置/修改变量值"
    default_config = {"variable": "", "value": None, "mode": "set"}  # mode: set / append / increment

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        var_name = self.config.get("variable", "")
        value = self.config.get("value")
        mode = self.config.get("mode", "set")

        if not var_name:
            return NodeResult(status=NodeStatus.FAILURE, error="变量名不能为空")

        if mode == "set":
            ctx.set_var(var_name, value)
        elif mode == "append":
            current = ctx.get_var(var_name, [])
            if isinstance(current, list):
                current.append(value)
            else:
                current = [current, value] if current is not None else [value]
            ctx.set_var(var_name, current)
        elif mode == "increment":
            current = ctx.get_var(var_name, 0)
            try:
                ctx.set_var(var_name, current + (value or 1))
            except TypeError as e:
                return NodeResult(status=NodeStatus.FAILURE, error=str(e))

        ctx.log(f"[variable_set] {var_name} = {ctx.get_var(var_name)}")
        return NodeResult(status=NodeStatus.SUCCESS, data={var_name: ctx.get_var(var_name)})

    def validate(self) -> bool:
        var_name = self.config.get("variable", "")
        mode = self.config.get("mode", "set")
        return isinstance(var_name, str) and len(var_name) > 0 and mode in ("set", "append", "increment")


class TextOutputNode(BaseNode):
    """文本输出节点 —— 将文本输出到日志或界面。"""
    node_type = "text_output"
    node_category = "数据"
    node_description = "输出文本到日志（支持变量插值）"
    default_config = {"text": "", "level": "info"}  # level: info / warning / error

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        import re

        text_template = self.config.get("text", "")
        level = self.config.get("level", "info")

        # 变量插值：{{var_name}} → 实际值
        def interpolate(m: re.Match) -> str:
            var_name = m.group(1)
            return str(ctx.get_var(var_name, f"{{{{{var_name}}}}}"))

        text = re.sub(r"\{\{(\w+)\}\}", interpolate, text_template)
        ctx.log(f"[text_output] [{level}] {text}")

        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"text": text, "level": level},
        )

    def validate(self) -> bool:
        level = self.config.get("level", "info")
        return level in ("info", "warning", "error")
