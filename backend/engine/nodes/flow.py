"""流程控制节点 — start, end, wait, condition, loop"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import register_node

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


@register_node("start", "流程控制", "开始", "脚本起始节点，标记流程入口")
class StartNode(BaseNode):
    """开始节点 — 不做任何操作，仅标记脚本入口"""
    default_config = {}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        ctx.log("▶ 脚本开始")
        return NodeResult.ok()

    def validate(self) -> bool:
        return True


@register_node("end", "流程控制", "结束", "脚本结束节点，标记流程出口")
class EndNode(BaseNode):
    """结束节点 — 停止执行上下文"""
    default_config = {}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        ctx.log("⏹ 脚本结束")
        ctx.stop()
        return NodeResult.ok()

    def validate(self) -> bool:
        return True


@register_node("wait", "流程控制", "等待", "等待指定时长（秒）")
class WaitNode(BaseNode):
    """等待节点 — 暂停执行指定时长

    Config:
        duration: 等待时长，单位秒（默认 1.0）
    """
    default_config = {"duration": 1.0}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        duration = float(self.config.get("duration", 1.0))
        ctx.log(f"⏳ 等待 {duration:.1f}s")
        await asyncio.sleep(duration)
        return NodeResult.ok()

    def validate(self) -> bool:
        duration = self.config.get("duration", 0)
        return isinstance(duration, (int, float)) and duration >= 0


@register_node("condition", "流程控制", "条件分支", "根据条件表达式选择下一个节点")
class ConditionNode(BaseNode):
    """条件节点 — 根据 expression 求值结果选择分支

    Config:
        expression: 条件表达式（支持变量替换，如 "$var >= 5"）
        true_branch: 条件为真时的下一个节点 ID（可选，不填则用 next_nodes[0]）
        false_branch: 条件为假时的下一个节点 ID（可选，不填则用 next_nodes[1]）

    也可以通过 condition 属性设置条件表达式。
    """
    default_config = {
        "expression": "",
        "true_branch": None,
        "false_branch": None,
    }

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        expression = self.condition or self.config.get("expression", "")
        result = self._evaluate(expression, ctx)
        ctx.log(f"🔀 条件 «{expression}» → {'真' if result else '假'}")

        if result:
            next_id = self.config.get("true_branch") or (self.next_nodes[0] if self.next_nodes else None)
        else:
            next_id = self.config.get("false_branch") or (self.next_nodes[1] if len(self.next_nodes) > 1 else None)

        return NodeResult.ok(next_node=next_id, condition_result=result)

    def _evaluate(self, expression: str, ctx: "ExecutionContext") -> bool:
        """简单条件求值：替换变量后执行 Python eval（受限环境）"""
        expr = expression.strip()
        if not expr:
            return True

        # 替换 $var / ${var} 形式的变量引用
        import re
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            value = ctx.get_var(var_name)
            if value is None:
                return "None"
            if isinstance(value, str):
                return repr(value)
            return str(value)

        expr = re.sub(r'\$\{(\w+(?:\.\w+)*)\}', replace_var, expr)
        expr = re.sub(r'\$(\w+(?:\.\w+)*)', replace_var, expr)

        # 安全求值：仅允许 safe_builtins
        safe_builtins = {"True": True, "False": False, "None": None}
        try:
            return bool(eval(expr, {"__builtins__": safe_builtins}, {}))
        except Exception:
            ctx.log(f"⚠ 条件表达式求值失败: {expression}", "warn")
            return False

    def validate(self) -> bool:
        expression = self.condition or self.config.get("expression", "")
        return bool(expression)


@register_node("loop", "流程控制", "循环", "按条件或次数重复执行子流程")
class LoopNode(BaseNode):
    """循环节点 — 控制子流程的重复执行

    Config:
        max_iterations: 最大循环次数（0 = 无限循环，需配合条件使用）
        condition: 继续循环的条件表达式（为空时仅靠 max_iterations 控制）
        counter_var: 循环计数器变量名（默认 "_loop_index"）
    """
    default_config = {
        "max_iterations": 0,
        "condition": "",
        "counter_var": "_loop_index",
    }

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        max_iter = int(self.config.get("max_iterations", 0))
        condition = self.config.get("condition", "")
        counter_var = self.config.get("counter_var", "_loop_index")

        iteration = ctx.get_var(counter_var, 0)
        ctx.log(f"🔁 循环节点（第 {iteration + 1} 次）")

        # 检查是否达到最大次数
        if max_iter > 0 and iteration >= max_iter:
            ctx.log(f"🔁 已达最大循环次数 {max_iter}，退出循环")
            ctx.delete_var(counter_var)
            # 循环结束后走 next_nodes[1]（若有），否则走 [0]
            exit_node = self.next_nodes[1] if len(self.next_nodes) > 1 else (self.next_nodes[0] if self.next_nodes else None)
            return NodeResult.ok(next_node=exit_node)

        # 检查条件
        if condition:
            from engine.nodes.flow import ConditionNode
            cond_node = ConditionNode(condition=condition)
            if not cond_node._evaluate(condition, ctx):
                ctx.log(f"🔁 循环条件不满足，退出循环")
                ctx.delete_var(counter_var)
                exit_node = self.next_nodes[1] if len(self.next_nodes) > 1 else (self.next_nodes[0] if self.next_nodes else None)
                return NodeResult.ok(next_node=exit_node)

        # 递增计数器，继续循环体
        ctx.set_var(counter_var, iteration + 1)
        # 循环体入口为 next_nodes[0]
        loop_body = self.next_nodes[0] if self.next_nodes else None
        return NodeResult.ok(next_node=loop_body, iteration=iteration + 1)

    def validate(self) -> bool:
        max_iter = self.config.get("max_iterations", 0)
        if not isinstance(max_iter, int) or max_iter < 0:
            return False
        return True
