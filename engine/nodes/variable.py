"""变量和文本操作节点"""

import asyncio
from engine.nodes.base import BaseNode, NodeResult, NodeStatus


class VariableSetNode(BaseNode):
    """变量设置节点 — 在上下文中设置或修改变量"""
    node_type = "variable_set"

    async def execute(self, ctx) -> NodeResult:
        key = self.config.get("key", "")
        value = self.config.get("value", "")
        expression = self.config.get("expression", "")
        ctx.info(f"设置变量 {key} = {value or expression}", self.node_id)
        if key:
            if expression:
                try:
                    resolved = eval(expression, {"__builtins__": {}},
                                    {"vars": ctx.get_all_variables()})
                except Exception:
                    resolved = expression
                ctx.set_var(key, resolved)
            else:
                ctx.set_var(key, value)
        ctx.set_node_output(self.node_id, {key: ctx.get_var(key)})
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return bool(self.config.get("key"))


class TextOutputNode(BaseNode):
    """文本输出节点 — 模拟键盘输入一段文本"""
    node_type = "text_output"

    async def execute(self, ctx) -> NodeResult:
        text = self.config.get("text", "")
        interval = float(self.config.get("interval", 0.05))
        preview = text[:50] + ("..." if len(text) > 50 else "")
        ctx.info(f"输入文本 ({len(text)}字符): {preview}", self.node_id)
        simulated_chars = min(len(text), 100)
        if simulated_chars > 0:
            await asyncio.sleep(interval * simulated_chars)
        return NodeResult(status=NodeStatus.SUCCESS, data={"char_count": len(text)})

    def validate(self) -> bool:
        text = self.config.get("text", "")
        return isinstance(text, str) and len(text) > 0
