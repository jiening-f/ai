"""测试 engine/executor/hooks.py — HookSystem 和内置钩子工厂"""

import pytest
import asyncio

from engine.executor.context import ExecutionContext
from engine.executor.hooks import (
    HookSystem,
    create_logging_hooks,
    create_performance_hooks,
    create_anti_detect_hook,
)
from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.nodes.flow import StartNode


# ═══════════════════════════════════════════════════════════════
# HookSystem 基础测试
# ═══════════════════════════════════════════════════════════════

class TestHookSystem:
    def test_initial_state(self):
        hooks = HookSystem()
        assert len(hooks._pre_hooks) == 0
        assert len(hooks._post_hooks) == 0

    def test_on_pre_execute(self):
        hooks = HookSystem()
        called = []

        @hooks.on_pre_execute
        def my_hook(node, ctx):
            called.append(node.node_id)

        assert len(hooks._pre_hooks) == 1
        assert hooks._pre_hooks[0] is my_hook

    def test_on_post_execute(self):
        hooks = HookSystem()
        called = []

        @hooks.on_post_execute
        def my_hook(node, ctx, result):
            called.append(result.status.value)

        assert len(hooks._post_hooks) == 1

    def test_remove_pre_hook(self):
        hooks = HookSystem()

        @hooks.on_pre_execute
        def h(node, ctx):
            pass

        assert len(hooks._pre_hooks) == 1
        hooks.remove_pre_hook(h)
        assert len(hooks._pre_hooks) == 0

    def test_remove_nonexistent_hook(self):
        hooks = HookSystem()

        def h(node, ctx):
            pass

        hooks.remove_pre_hook(h)  # 不应报错

    @pytest.mark.asyncio
    async def test_run_pre_hooks_empty(self):
        hooks = HookSystem()
        ctx = ExecutionContext()
        node = StartNode("s")
        result = await hooks.run_pre_hooks(node, ctx)
        assert result is None  # 无线程时正常执行

    @pytest.mark.asyncio
    async def test_run_pre_hooks_intercept(self):
        """pre 钩子可以拦截执行"""
        hooks = HookSystem()

        @hooks.on_pre_execute
        def intercept(node, ctx):
            return NodeResult(status=NodeStatus.SKIPPED, data="intercepted")

        ctx = ExecutionContext()
        node = StartNode("s")
        result = await hooks.run_pre_hooks(node, ctx)
        assert result is not None
        assert result.status == NodeStatus.SKIPPED
        assert result.data == "intercepted"

    @pytest.mark.asyncio
    async def test_run_pre_hooks_exception(self):
        """钩子异常不应阻断流程"""
        hooks = HookSystem()

        @hooks.on_pre_execute
        def bad_hook(node, ctx):
            raise RuntimeError("hook error")

        ctx = ExecutionContext()
        node = StartNode("s")
        result = await hooks.run_pre_hooks(node, ctx)
        assert result is None  # 异常被吞掉

    @pytest.mark.asyncio
    async def test_run_post_hooks(self):
        hooks = HookSystem()
        post_results = []

        @hooks.on_post_execute
        def record(node, ctx, result):
            post_results.append(result.status.value)

        ctx = ExecutionContext()
        node = StartNode("s")
        result = NodeResult(status=NodeStatus.SUCCESS)
        await hooks.run_post_hooks(node, ctx, result)
        assert post_results == ["success"]

    @pytest.mark.asyncio
    async def test_run_post_hooks_exception(self):
        """post 钩子异常不应阻断"""
        hooks = HookSystem()

        @hooks.on_post_execute
        def bad_hook(node, ctx, result):
            raise RuntimeError("boom")

        ctx = ExecutionContext()
        node = StartNode("s")
        result = NodeResult(status=NodeStatus.SUCCESS)
        # 不应抛异常
        await hooks.run_post_hooks(node, ctx, result)

    @pytest.mark.asyncio
    async def test_multiple_hooks_ordered(self):
        """多个钩子按注册顺序执行"""
        hooks = HookSystem()
        order = []

        @hooks.on_pre_execute
        def first(node, ctx):
            order.append("first")

        @hooks.on_pre_execute
        def second(node, ctx):
            order.append("second")

        ctx = ExecutionContext()
        node = StartNode("s")
        await hooks.run_pre_hooks(node, ctx)
        assert order == ["first", "second"]

    def test_clear(self):
        hooks = HookSystem()

        @hooks.on_pre_execute
        def h1(node, ctx):
            pass

        @hooks.on_post_execute
        def h2(node, ctx, result):
            pass

        hooks.clear()
        assert len(hooks._pre_hooks) == 0
        assert len(hooks._post_hooks) == 0


# ═══════════════════════════════════════════════════════════════
# 内置钩子工厂测试
# ═══════════════════════════════════════════════════════════════

class TestLoggingHooks:
    def test_create_logging_hooks(self):
        pre, post = create_logging_hooks()
        assert callable(pre)
        assert callable(post)

    def test_pre_log_hook(self):
        pre, _ = create_logging_hooks()
        ctx = ExecutionContext()
        node = StartNode("test_start")
        result = pre(node, ctx)
        assert result is None  # pre 钩子不拦截

        logs = ctx.get_logs()
        assert any("执行" in log["message"] for log in logs)

    def test_post_log_hook_success(self):
        _, post = create_logging_hooks()
        ctx = ExecutionContext()
        node = StartNode("test_start")
        result = NodeResult(status=NodeStatus.SUCCESS)
        post(node, ctx, result)

        logs = ctx.get_logs()
        assert any("OK" in log["message"] for log in logs)

    def test_post_log_hook_failed(self):
        _, post = create_logging_hooks()
        ctx = ExecutionContext()
        node = StartNode("bad")
        result = NodeResult(status=NodeStatus.FAILED, error="test error")
        post(node, ctx, result)

        logs = ctx.get_logs()
        assert any("FAIL" in log["message"] for log in logs)
        assert any("test error" in log["message"] for log in logs)


class TestPerformanceHooks:
    def test_create_performance_hooks(self):
        pre, post = create_performance_hooks()
        assert callable(pre)
        assert callable(post)

    def test_pre_post_cycle(self):
        pre, post = create_performance_hooks()
        ctx = ExecutionContext()
        node = StartNode("n1")

        # pre 记录时间
        pre(node, ctx)
        # post 记录耗时
        result = NodeResult(status=NodeStatus.SUCCESS)
        post(node, ctx, result)

        logs = ctx.get_logs()
        assert any("耗时" in log["message"] for log in logs)

    def test_post_without_pre(self):
        """无 pre 时 post 应安全跳过"""
        _, post = create_performance_hooks()
        ctx = ExecutionContext()
        node = StartNode("n1")
        result = NodeResult(status=NodeStatus.SUCCESS)
        # 不应报错（没有 pre 对应的计时器）
        post(node, ctx, result)


class TestAntiDetectHook:
    def test_create_anti_detect_hook(self):
        hook = create_anti_detect_hook(0.001, 0.005)
        assert callable(hook)

    def test_anti_detect_executes(self):
        hook = create_anti_detect_hook(0.001, 0.002)
        ctx = ExecutionContext()
        node = StartNode("s")
        import time
        start = time.time()
        hook(node, ctx)
        elapsed = time.time() - start
        # 延迟应该在范围内
        assert 0 <= elapsed < 0.5  # 宽松起见

    def test_default_delay_range(self):
        hook = create_anti_detect_hook()
        ctx = ExecutionContext()
        node = StartNode("s")
        import time
        start = time.time()
        hook(node, ctx)
        elapsed = time.time() - start
        # 应该在 0.01~0.08 之间
        assert 0 <= elapsed < 0.5
