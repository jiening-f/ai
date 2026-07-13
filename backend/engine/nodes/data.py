"""数据节点 — variable_set, text_output"""

from __future__ import annotations
from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import register_node

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


@register_node("variable_set", "数据", "设置变量", "设置或修改变量值")
class VariableSetNode(BaseNode):
    """变量设置节点 — 在上下文中设置变量值

    Config:
        name: 变量名
        value: 变量值（支持字符串、数字、布尔值）
    """
    default_config = {"name": ..., "value": ""}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        name = str(self.config.get("name", ""))
        value = self.config.get("value", "")
        if not name:
            return NodeResult.fail("未指定变量名")
        ctx.set_var(name, value)
        ctx.log(f"📝 变量: {name} = {value!r}")
        return NodeResult.ok(variable=name, value=value)

    def validate(self) -> bool:
        name = self.config.get("name")
        return name is not None and str(name).strip() != ""


@register_node("text_output", "数据", "文本输出", "向日志输出一段文本")
class TextOutputNode(BaseNode):
    """文本输出节点 — 向执行日志输出内容

    Config:
        text: 要输出的文本（支持 $变量名 引用）
        level: 日志级别（"info" / "warn" / "error"，默认 "info"）
    """
    default_config = {"text": ..., "level": "info"}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        text = str(self.config.get("text", ""))
        level = str(self.config.get("level", "info"))
        # 替换 $变量名 引用
        resolved_text = self._resolve_text(text, ctx)
        ctx.log(f"💬 {resolved_text}", level=level)
        return NodeResult.ok(text=resolved_text)

    def _resolve_text(self, text: str, ctx: "ExecutionContext") -> str:
        """替换文本中的 $var 变量引用"""
        import re
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            value = ctx.get_var(var_name)
            return str(value) if value is not None else match.group(0)
        text = re.sub(r'\$\{(\w+(?:\.\w+)*)\}', replace_var, text)
        text = re.sub(r'\$(\w+(?:\.\w+)*)', replace_var, text)
        return text

    def validate(self) -> bool:
        text = self.config.get("text")
        return text is not None and str(text).strip() != ""
