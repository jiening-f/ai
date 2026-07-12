"""
流程控制节点

- StartNode: 开始节点（流程入口，无实际操作）
- EndNode: 结束节点（标记流程结束）
- WaitNode: 等待节点（延迟指定毫秒）
- ConditionNode: 条件判断节点（根据变量值分支）
- LoopNode: 循环节点（条件满足时循环执行）
"""

import asyncio
from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class StartNode(BaseNode):
    """脚本开始节点，标记流程入口"""

    node_type = "start"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.log(f"[开始] 脚本开始执行")
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"label": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "开始",
            "category": "流程控制",
            "description": "脚本流程的入口节点，一个脚本有且仅有一个开始节点",
            "config_schema": {"label": {"type": "string", "default": "", "description": "节点标签"}},
        }


class EndNode(BaseNode):
    """脚本结束节点，标记流程结束"""

    node_type = "end"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.log(f"[结束] 脚本执行完毕")
        return NodeResult(success=True, next_node_id=None)

    @classmethod
    def default_config(cls) -> dict:
        return {"label": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "结束",
            "category": "流程控制",
            "description": "脚本流程的结束节点，到达此节点后脚本停止执行",
            "config_schema": {"label": {"type": "string", "default": "", "description": "节点标签"}},
        }


class WaitNode(BaseNode):
    """等待节点：延迟指定毫秒后继续"""

    node_type = "wait"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        duration_ms = self.config.get("duration_ms", 1000)
        ctx.log(f"[等待] 等待 {duration_ms}ms")
        await asyncio.sleep(duration_ms / 1000.0)
        return NodeResult(success=True)

    def validate(self) -> bool:
        duration = self.config.get("duration_ms", 0)
        return isinstance(duration, (int, float)) and duration >= 0

    @classmethod
    def default_config(cls) -> dict:
        return {"duration_ms": 1000}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "等待",
            "category": "流程控制",
            "description": "暂停执行指定毫秒数",
            "config_schema": {"duration_ms": {"type": "number", "default": 1000, "min": 0, "description": "等待毫秒数"}},
        }


class ConditionNode(BaseNode):
    """
    条件判断节点

    根据条件表达式（condition 字段）在上下文中求值，
    决定走哪个分支（next_nodes[0] 或 next_nodes[1]）。
    条件表达式示例: "$var_name == 'value'", "$count > 5"
    """

    node_type = "condition"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        if not self.condition:
            ctx.log("[条件] 无条件表达式，走默认分支")
            return NodeResult(success=True)

        # 在上下文中求值条件表达式
        result = _eval_condition(self.condition, ctx)
        ctx.log(f"[条件] '{self.condition}' → {result}")

        if result and len(self.next_nodes) > 0:
            return NodeResult(success=True, next_node_id=self.next_nodes[0])
        elif not result and len(self.next_nodes) > 1:
            return NodeResult(success=True, next_node_id=self.next_nodes[1])

        # 无对应分支，走默认
        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.condition)

    @classmethod
    def default_config(cls) -> dict:
        return {"expression": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "条件判断",
            "category": "流程控制",
            "description": "根据变量值决定执行分支，条件为真走 next_nodes[0]，为假走 next_nodes[1]",
            "config_schema": {"expression": {"type": "string", "default": "", "description": "条件表达式"}},
        }


class LogNode(BaseNode):
    """日志节点：在上下文中记录一条日志消息"""

    node_type = "log"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        message = self.config.get("message", "")
        level = self.config.get("level", "INFO")
        ctx.log(level, message, node_id=self.node_id)
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"message": "", "level": "INFO"}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "日志",
            "category": "流程控制",
            "description": "在上下文中记录一条日志消息",
            "config_schema": {
                "message": {"type": "string", "default": "", "description": "日志消息"},
                "level": {"type": "string", "default": "INFO", "description": "日志级别"},
            },
        }


class LoopNode(BaseNode):
    """
    循环节点

    配置 loop_times（循环次数）或 loop_condition（循环条件），
    条件满足时跳转到目标节点执行。
    """

    node_type = "loop"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        loop_key = f"_loop_count_{self.node_id}"
        current_count = ctx.get_var(loop_key, 0) + 1
        ctx.set_var(loop_key, current_count)

        max_times = self.config.get("loop_times", 0)
        loop_condition = self.config.get("loop_condition", "")

        should_continue = False
        if max_times > 0 and current_count < max_times:
            should_continue = True
        elif loop_condition:
            should_continue = _eval_condition(loop_condition, ctx)

        ctx.log(f"[循环] 第 {current_count} 次，继续: {should_continue}")

        if should_continue:
            target = self.config.get("loop_target", "")
            return NodeResult(success=True, next_node_id=target or None)
        else:
            ctx.set_var(loop_key, 0)  # 重置计数器
            return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("loop_times") or self.config.get("loop_condition"))

    @classmethod
    def default_config(cls) -> dict:
        return {"loop_times": 0, "loop_condition": "", "loop_target": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "循环",
            "category": "流程控制",
            "description": "按次数或条件循环执行指定节点",
            "config_schema": {
                "loop_times": {"type": "number", "default": 0, "description": "循环次数，0 表示不限"},
                "loop_condition": {"type": "string", "default": "", "description": "循环条件表达式"},
                "loop_target": {"type": "string", "default": "", "description": "循环目标节点 ID"},
            },
        }


def _eval_condition(expression: str, ctx: ExecutionContext) -> bool:
    """
    在上下文中安全地求值条件表达式

    支持的格式：
    - "$var == 'value'" — 变量等于某值
    - "$var != 'value'" — 变量不等于
    - "$var > N" / "$var < N" — 数值比较
    - "$var" — 变量为真值（非空、非零）

    安全限制：不使用 eval()，仅解析简单表达式。
    """
    import re

    expr = expression.strip()

    # 匹配运算符
    match = re.match(r'\$(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)', expr)
    if match:
        var_name = match.group(1)
        op = match.group(2)
        raw_value = match.group(3).strip().strip("'").strip('"')

        var_value = ctx.get_var(var_name, "")

        # 尝试数值比较
        try:
            var_num = float(var_value)
            cmp_num = float(raw_value)
            if op == "==": return var_num == cmp_num
            if op == "!=": return var_num != cmp_num
            if op == ">": return var_num > cmp_num
            if op == "<": return var_num < cmp_num
            if op == ">=": return var_num >= cmp_num
            if op == "<=": return var_num <= cmp_num
        except (ValueError, TypeError):
            pass

        # 字符串比较
        if op == "==": return str(var_value) == raw_value
        if op == "!=": return str(var_value) != raw_value
        return False

    # 简单变量真值判断: $var
    match = re.match(r'\$(\w+)$', expr)
    if match:
        var_name = match.group(1)
        var_value = ctx.get_var(var_name)
        return bool(var_value)

    return False
