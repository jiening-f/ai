"""内置基础节点：start、end、wait、log"""

from engine.nodes.base import BaseNode, NodeResult, NodeStatus


class StartNode(BaseNode):
    """流程开始节点 — 流程起点，直接通过"""
    node_type = "start"

    async def execute(self, ctx) -> NodeResult:
        ctx.info("流程开始", self.node_id)
        return NodeResult(status=NodeStatus.SUCCESS)


class EndNode(BaseNode):
    """流程结束节点 — 流程终点"""
    node_type = "end"

    async def execute(self, ctx) -> NodeResult:
        ctx.info("流程结束", self.node_id)
        return NodeResult(status=NodeStatus.SUCCESS, next_node=None)


class WaitNode(BaseNode):
    """等待节点 — 等待指定时长"""
    node_type = "wait"

    async def execute(self, ctx) -> NodeResult:
        import asyncio
        duration = float(self.config.get("duration", 1.0))
        ctx.info(f"等待 {duration}s", self.node_id)
        await asyncio.sleep(min(duration, 60))  # 最多 60 秒
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        duration = self.config.get("duration", 0)
        return isinstance(duration, (int, float)) and duration >= 0


class LogNode(BaseNode):
    """日志节点 — 输出一条日志消息"""
    node_type = "log"

    async def execute(self, ctx) -> NodeResult:
        message = self.config.get("message", "")
        level = self.config.get("level", "INFO")
        ctx.log(level, message, self.node_id)
        return NodeResult(status=NodeStatus.SUCCESS)


class ConditionNode(BaseNode):
    """条件分支节点 — 根据条件表达式选择分支

    配置:
        condition: Python 表达式字符串，可用变量 ctx.get_var('key')
        true_branch: 条件为真时的下一个节点 id
        false_branch: 条件为假时的下一个节点 id
    """
    node_type = "condition"

    async def execute(self, ctx) -> NodeResult:
        expression = self.config.get("condition", "True")
        try:
            # 安全求值：受限的变量作用域
            safe_globals = {"__builtins__": {}}
            safe_locals = {"ctx": ctx, "vars": ctx.get_all_variables()}
            result = eval(expression, safe_globals, safe_locals)
        except Exception as e:
            return NodeResult(
                status=NodeStatus.FAILED,
                error=f"条件表达式求值失败: {e}",
            )

        if result:
            ctx.info(f"条件为真: {expression}", self.node_id)
            return NodeResult(status=NodeStatus.SUCCESS)
        else:
            ctx.info(f"条件为假: {expression}", self.node_id)
            return NodeResult(status=NodeStatus.SKIPPED)

    def get_next_node(self, result: NodeResult) -> str:
        if result.status == NodeStatus.SUCCESS:
            return self.config.get("true_branch") or (
                self.next_nodes[0] if self.next_nodes else None
            )
        else:
            return self.config.get("false_branch") or (
                self.next_nodes[1] if len(self.next_nodes) > 1 else None
            )


class LoopNode(BaseNode):
    """循环节点 — 条件满足时回到指定节点

    配置:
        condition: Python 表达式
        loop_target: 循环回到的节点 id
        max_iterations: 最大迭代次数（0=无限）
    """
    node_type = "loop"

    async def execute(self, ctx) -> NodeResult:
        expression = self.config.get("condition", "True")
        max_iter = int(self.config.get("max_iterations", 0))

        # 检查迭代次数
        counter_key = f"_loop_{self.node_id}_count"
        count = ctx.get_var(counter_key, 0)

        if max_iter > 0 and count >= max_iter:
            ctx.info(f"循环已达上限 {max_iter}，退出", self.node_id)
            return NodeResult(status=NodeStatus.SUCCESS)

        try:
            safe_globals = {"__builtins__": {}}
            safe_locals = {"ctx": ctx, "vars": ctx.get_all_variables()}
            should_loop = eval(expression, safe_globals, safe_locals)
        except Exception as e:
            return NodeResult(
                status=NodeStatus.FAILED,
                error=f"循环条件求值失败: {e}",
            )

        if should_loop:
            ctx.set_var(counter_key, count + 1)
            loop_target = self.config.get("loop_target", "")
            ctx.info(f"循环 #{count + 1} → {loop_target}", self.node_id)
            return NodeResult(
                status=NodeStatus.SUCCESS,
                next_node=loop_target or None,
            )
        else:
            ctx.info("循环条件不满足，退出", self.node_id)
            return NodeResult(status=NodeStatus.SUCCESS)
