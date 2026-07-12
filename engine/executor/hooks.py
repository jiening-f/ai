"""钩子系统 — 节点执行生命周期的可扩展回调

支持在节点执行前后注入自定义逻辑，用于：
- 日志记录
- 性能监控
- 反检测（随机延迟）
- 截图快照
- 自定义验证
"""

from __future__ import annotations
from typing import Any, Callable, Optional
from engine.executor.context import ExecutionContext
from engine.nodes.base import BaseNode, NodeResult


# 回调类型定义
PreExecuteHook = Callable[[BaseNode, ExecutionContext], Optional[NodeResult]]
"""pre_execute 回调：返回 NodeResult 可跳过实际执行"""

PostExecuteHook = Callable[[BaseNode, ExecutionContext, NodeResult], None]
"""post_execute 回调：接收执行结果，可修改上下文"""


class HookSystem:
    """可扩展的钩子系统

    用法:
        hooks = HookSystem()
        hooks.on_pre_execute(lambda node, ctx: log(f"执行前: {node.node_id}"))
        hooks.on_post_execute(lambda node, ctx, res: log(f"执行后: {res.status}"))

        # 在 runner 中使用
        result = await hooks.run_pre_hooks(node, ctx)
        if result is None:
            result = await node.execute(ctx)
        await hooks.run_post_hooks(node, ctx, result)
    """

    def __init__(self):
        self._pre_hooks: list[PreExecuteHook] = []
        self._post_hooks: list[PostExecuteHook] = []

    def on_pre_execute(self, hook: PreExecuteHook):
        """注册 pre_execute 钩子（按注册顺序执行）"""
        self._pre_hooks.append(hook)
        return hook  # 返回 hook 方便用作装饰器

    def on_post_execute(self, hook: PostExecuteHook):
        """注册 post_execute 钩子"""
        self._post_hooks.append(hook)
        return hook

    def remove_pre_hook(self, hook: PreExecuteHook):
        """移除 pre_execute 钩子"""
        if hook in self._pre_hooks:
            self._pre_hooks.remove(hook)

    def remove_post_hook(self, hook: PostExecuteHook):
        """移除 post_execute 钩子"""
        if hook in self._post_hooks:
            self._post_hooks.remove(hook)

    async def run_pre_hooks(
        self, node: BaseNode, ctx: ExecutionContext
    ) -> Optional[NodeResult]:
        """执行所有 pre_execute 钩子

        如果任一钩子返回 NodeResult，则跳过节点实际执行，
        直接使用该结果。返回 None 表示正常执行。
        """
        for hook in self._pre_hooks:
            try:
                result = hook(node, ctx)
                if result is not None:
                    return result
            except Exception as e:
                ctx.warn(f"pre_hook 异常: {e}", node.node_id)
        return None

    async def run_post_hooks(
        self, node: BaseNode, ctx: ExecutionContext, result: NodeResult
    ):
        """执行所有 post_execute 钩子"""
        for hook in self._post_hooks:
            try:
                hook(node, ctx, result)
            except Exception as e:
                ctx.warn(f"post_hook 异常: {e}", node.node_id)

    def clear(self):
        """清空所有钩子"""
        self._pre_hooks.clear()
        self._post_hooks.clear()


# ── 内置钩子工厂 ──

def create_logging_hooks(on_log: Callable[[str], None] = print):
    """创建日志记录钩子"""
    def pre_log(node: BaseNode, ctx: ExecutionContext):
        ctx.info(f"执行 [{node.node_type}] {node.node_id}", node.node_id)

    def post_log(node: BaseNode, ctx: ExecutionContext, result: NodeResult):
        status = "OK" if result.status.value == "success" else "FAIL"
        msg = f"[{status}] [{node.node_type}] {node.node_id} -> {result.status.value}"
        if result.error:
            msg += f" ({result.error})"
        ctx.info(msg, node.node_id)

    pre_log.__name__ = "pre_log"
    post_log.__name__ = "post_log"
    return pre_log, post_log


def create_anti_detect_hook(min_delay: float = 0.01, max_delay: float = 0.08):
    """创建反检测延迟钩子（模拟人类操作间隔）"""
    import random

    def anti_detect(node: BaseNode, ctx: ExecutionContext):
        import asyncio
        # 同步延迟（在 async 上下文中用 time.sleep 即可，钩子是同步回调）
        import time
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    anti_detect.__name__ = "anti_detect"
    return anti_detect


def create_performance_hooks():
    """创建性能监控钩子"""
    import time

    _timers: dict[str, float] = {}

    def pre_perf(node: BaseNode, ctx: ExecutionContext):
        _timers[node.node_id] = time.time()

    def post_perf(node: BaseNode, ctx: ExecutionContext, result: NodeResult):
        if node.node_id in _timers:
            elapsed = (time.time() - _timers[node.node_id]) * 1000
            ctx.info(f"耗时 {elapsed:.1f}ms", node.node_id,
                     data={"elapsed_ms": elapsed})
            del _timers[node.node_id]

    pre_perf.__name__ = "pre_perf"
    post_perf.__name__ = "post_perf"
    return pre_perf, post_perf
