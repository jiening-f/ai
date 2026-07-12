"""流程控制节点：start, end, wait, condition, loop。"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class StartNode(BaseNode):
    """起始节点 —— 脚本入口，无条件通过。"""
    node_type = "start"
    node_category = "流程控制"
    node_description = "脚本起始节点，标记流程入口"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.log(f"[start] 脚本开始执行")
        return NodeResult(status=NodeStatus.SUCCESS, data={"entry_time": ctx.start_time})


class EndNode(BaseNode):
    """结束节点 —— 终止脚本执行。"""
    node_type = "end"
    node_category = "流程控制"
    node_description = "脚本终止节点，停止整个流程"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.log(f"[end] 脚本执行结束")
        ctx.stop()
        return NodeResult(status=NodeStatus.SUCCESS)


class WaitNode(BaseNode):
    """等待节点 —— 暂停指定时长。"""
    node_type = "wait"
    node_category = "流程控制"
    node_description = "等待指定时长（毫秒）后继续"
    default_config = {"duration_ms": 1000}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        duration = self.config.get("duration_ms", 1000)
        ctx.log(f"[wait] 等待 {duration}ms")
        await asyncio.sleep(duration / 1000)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        duration = self.config.get("duration_ms")
        return isinstance(duration, (int, float)) and duration > 0


class ConditionNode(BaseNode):
    """条件判断节点 —— 根据表达式选择分支。"""
    node_type = "condition"
    node_category = "流程控制"
    node_description = "根据条件表达式选择不同分支路径"
    default_config = {"expression": ""}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        expression = self.config.get("expression", "")
        # 简单表达式求值：支持 == != > < >= <=
        try:
            result = self._eval_expression(expression, ctx.variables)
        except Exception as e:
            ctx.log(f"[condition] 表达式求值失败: {e}")
            return NodeResult(status=NodeStatus.FAILURE, error=str(e))

        ctx.log(f"[condition] '{expression}' → {result}")
        # next_nodes[0] 是 true 分支，next_nodes[1] 是 false 分支
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"result": result},
            next_node=self.next_nodes[0] if result else (self.next_nodes[1] if len(self.next_nodes) > 1 else None),
        )

    @staticmethod
    def _eval_expression(expr: str, variables: dict[str, Any]) -> bool:
        """安全地求值简单布尔表达式。"""
        import re
        # 替换变量引用 {{var}} → 实际值
        def replace_var(m: re.Match) -> str:
            var_name = m.group(1)
            val = variables.get(var_name, "None")
            return repr(val)

        expr = re.sub(r"\{\{(\w+)\}\}", replace_var, expr)
        # 仅允许安全的内置函数
        safe_globals = {"__builtins__": {"True": True, "False": False, "None": None}}
        return bool(eval(expr, safe_globals, {}))

    def validate(self) -> bool:
        return bool(self.config.get("expression")) and len(self.next_nodes) >= 2


class LoopNode(BaseNode):
    """循环节点 —— 重复执行子流程。"""
    node_type = "loop"
    node_category = "流程控制"
    node_description = "按次数或条件循环执行子流程"
    default_config = {"max_iterations": 10, "loop_expression": ""}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        max_iter = self.config.get("max_iterations", 10)
        loop_expr = self.config.get("loop_expression", "")

        iteration = ctx.get_var("__loop_iteration__", 0)
        ctx.log(f"[loop] 迭代 {iteration + 1}/{max_iter}")

        # 检查退出条件
        if iteration >= max_iter:
            ctx.delete_var("__loop_iteration__")
            ctx.log("[loop] 达到最大迭代次数")
            return NodeResult(status=NodeStatus.SUCCESS)

        if loop_expr:
            try:
                should_continue = ConditionNode._eval_expression(loop_expr, ctx.variables)
                if not should_continue:
                    ctx.delete_var("__loop_iteration__")
                    ctx.log("[loop] 循环条件不满足，退出")
                    return NodeResult(status=NodeStatus.SUCCESS)
            except Exception:
                pass

        ctx.set_var("__loop_iteration__", iteration + 1)
        # 返回第一个后继节点（进入循环体），循环体结束后通过 LoopEnd 回到这里
        return NodeResult(status=NodeStatus.SUCCESS, data={"iteration": iteration + 1})

    def validate(self) -> bool:
        max_iter = self.config.get("max_iterations", 0)
        return isinstance(max_iter, int) and max_iter > 0
