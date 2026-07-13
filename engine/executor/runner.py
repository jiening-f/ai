"""异步脚本执行引擎 — 核心执行循环和状态机

状态机: idle → running → paused/stopped/completed/error
支持:
- 异步执行循环（从 start 节点开始，按图遍历）
- 条件分支（condition 节点）
- 循环（loop 节点）
- 暂停/恢复/停止/单步调试
- 错误处理（on_error: stop/continue/retry）
"""

from __future__ import annotations
import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional

from engine.executor.context import ExecutionContext
from engine.executor.hooks import HookSystem
from engine.nodes.base import BaseNode, NodeResult, NodeStatus


class EngineState(Enum):
    """引擎运行状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class ScriptRunner:
    """异步脚本执行引擎

    用法:
        nodes = {"start": start_node, "step1": step1_node, "end": end_node}
        runner = ScriptRunner(nodes, start_node_id="start")
        await runner.run()
    """

    def __init__(
        self,
        nodes: dict[str, BaseNode],
        start_node_id: str = "start",
        hooks: Optional[HookSystem] = None,
        on_error: str = "stop",
        max_retries: int = 0,
    ):
        """
        参数:
            nodes: 节点字典 {node_id: BaseNode}
            start_node_id: 起始节点 id
            hooks: 钩子系统
            on_error: 错误处理策略 ("stop" | "continue" | "retry")
            max_retries: retry 策略下的最大重试次数
        """
        self.nodes = nodes
        self.start_node_id = start_node_id
        self.hooks = hooks or HookSystem()
        self.on_error = on_error
        self.max_retries = max_retries

        # 运行时状态
        self._state = EngineState.IDLE
        self._ctx: Optional[ExecutionContext] = None
        self._current_node_id: Optional[str] = None
        self._loop_count = 0
        self._max_loops = 0  # 0 = 无限

        # 回调
        self._on_state_change: Optional[Callable] = None
        self._on_node_execute: Optional[Callable] = None

    # ── 属性 ──

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def current_node_id(self) -> Optional[str]:
        return self._current_node_id

    @property
    def context(self) -> Optional[ExecutionContext]:
        return self._ctx

    # ── 回调设置 ──

    def on_state_change(self, callback: Callable[[EngineState, EngineState], None]):
        """状态变化回调 func(old_state, new_state)"""
        self._on_state_change = callback

    def on_node_execute(self, callback: Callable[[str, NodeResult], None]):
        """节点执行回调 func(node_id, result)"""
        self._on_node_execute = callback

    # ── 状态切换 ──

    def _set_state(self, new_state: EngineState):
        old = self._state
        self._state = new_state
        if self._on_state_change:
            try:
                self._on_state_change(old, new_state)
            except Exception:
                pass

    # ── 控制方法 ──

    async def run(self) -> ExecutionContext:
        """启动执行（阻塞直到完成或停止）"""
        if self._state == EngineState.RUNNING:
            return self._ctx

        self._ctx = ExecutionContext()
        self._ctx.mark_start()
        self._set_state(EngineState.RUNNING)

        try:
            await self._execution_loop()
        except Exception as e:
            self._ctx.error(f"引擎异常: {e}")
            self._set_state(EngineState.ERROR)
        finally:
            self._ctx.running = False
            if self._state not in (EngineState.STOPPED, EngineState.ERROR):
                self._set_state(EngineState.COMPLETED)

        return self._ctx

    async def pause(self):
        """暂停执行（当前节点完成后暂停）"""
        if self._state == EngineState.RUNNING:
            self._ctx.pause()
            self._set_state(EngineState.PAUSED)

    async def resume(self):
        """从暂停恢复"""
        if self._state == EngineState.PAUSED:
            self._ctx.resume()
            self._set_state(EngineState.RUNNING)

    async def stop(self):
        """停止执行"""
        self._ctx.stop()
        self._set_state(EngineState.STOPPED)

    async def step(self):
        """单步执行（执行一个节点后自动暂停）"""
        if self._state in (EngineState.PAUSED, EngineState.IDLE):
            # B3 修复: 确保 _ctx 在使用前已初始化
            if self._ctx is None:
                self._ctx = ExecutionContext()
            self._ctx.enable_step_mode()
            if self._state == EngineState.IDLE:
                # 首次单步：启动执行循环
                self._ctx.mark_start()
                self._ctx.step_once()
                self._set_state(EngineState.RUNNING)
                try:
                    await self._execution_loop()
                except Exception as e:
                    self._ctx.error(f"引擎异常: {e}")
                    self._set_state(EngineState.ERROR)
            else:
                self._ctx.step_once()
                self._set_state(EngineState.RUNNING)

    # ── 执行循环 ──

    async def _execution_loop(self):
        """主执行循环：遍历节点图"""
        ctx = self._ctx

        # 验证：必须有 start 节点
        current_id = self.start_node_id
        if current_id not in self.nodes:
            ctx.error(f"起始节点 '{current_id}' 不存在")
            self._set_state(EngineState.ERROR)
            return

        self._loop_count = 0

        while ctx.is_active():
            self._loop_count += 1
            if self._max_loops > 0 and self._loop_count > self._max_loops:
                ctx.info(f"达到最大循环次数 {self._max_loops}，停止")
                break

            # 等待暂停恢复
            while ctx.paused and ctx.is_active():
                await asyncio.sleep(0.05)

            if not ctx.is_active():
                break

            # 获取当前节点
            node = self.nodes.get(current_id)
            if node is None:
                ctx.error(f"节点 '{current_id}' 不存在")
                self._set_state(EngineState.ERROR)
                break

            self._current_node_id = current_id
            ctx.mark_current_node(current_id)

            # 执行节点
            result = await self._execute_node(node, ctx)

            # 通知回调
            if self._on_node_execute:
                try:
                    self._on_node_execute(current_id, result)
                except Exception:
                    pass

            # 决定下一个节点
            next_id = node.get_next_node(result)

            if next_id is None:
                # 没有后续节点 → 流程结束
                ctx.info("流程结束（无后续节点）", current_id)
                break

            if result.status == NodeStatus.FAILED:
                if self.on_error == "stop":
                    ctx.error(f"节点执行失败，停止: {result.error}", current_id)
                    self._set_state(EngineState.ERROR)
                    break
                elif self.on_error == "continue":
                    ctx.warn(f"节点执行失败，跳过: {result.error}", current_id)
                elif self.on_error == "retry":
                    # B4 修复: retry 用尽后视为致命错误，停止执行
                    ctx.error(f"节点执行失败（重试已用尽），停止: {result.error}", current_id)
                    self._set_state(EngineState.ERROR)
                    break

            current_id = next_id

            # 单步模式：执行一个节点后自动暂停
            if ctx.step_mode:
                ctx.paused = True

    async def _execute_node(
        self, node: BaseNode, ctx: ExecutionContext
    ) -> NodeResult:
        """执行单个节点（含钩子和重试）"""
        retries = 0
        max_retries = self.max_retries if self.on_error == "retry" else 0

        while True:
            # ── pre_execute 钩子 ──
            hook_result = await self.hooks.run_pre_hooks(node, ctx)
            if hook_result is not None:
                return hook_result  # 钩子拦截了执行

            # ── 实际执行 ──
            try:
                result = await node.execute(ctx)
            except Exception as e:
                result = NodeResult(
                    status=NodeStatus.FAILED,
                    error=str(e),
                )
                ctx.error(f"节点执行异常: {e}", node.node_id)

            # ── post_execute 钩子 ──
            await self.hooks.run_post_hooks(node, ctx, result)

            # ── 统计 ──
            ctx.mark_executed(
                node.node_id,
                result.status == NodeStatus.SUCCESS,
            )

            # ── 重试逻辑 ──
            if result.status == NodeStatus.FAILED and retries < max_retries:
                retries += 1
                ctx.warn(
                    f"重试 {retries}/{max_retries}: {result.error}",
                    node.node_id,
                )
                await asyncio.sleep(0.3 * retries)  # 递增延迟
                continue

            return result


# ── 便捷工厂 ──

def create_runner(
    nodes: dict[str, BaseNode],
    start_node_id: str = "start",
    with_logging: bool = True,
    with_performance: bool = False,
    with_anti_detect: bool = False,
    on_error: str = "stop",
    max_retries: int = 0,
) -> ScriptRunner:
    """创建预配置的执行器

    参数:
        nodes: 节点字典
        start_node_id: 起始节点
        with_logging: 是否添加日志钩子
        with_performance: 是否添加性能钩子
        with_anti_detect: 是否添加反检测延迟
        on_error: 错误处理策略
        max_retries: 重试次数
    """
    from engine.executor.hooks import (
        create_logging_hooks,
        create_performance_hooks,
        create_anti_detect_hook,
    )

    hooks = HookSystem()

    if with_logging:
        pre, post = create_logging_hooks()
        hooks.on_pre_execute(pre)
        hooks.on_post_execute(post)

    if with_performance:
        pre, post = create_performance_hooks()
        hooks.on_pre_execute(pre)
        hooks.on_post_execute(post)

    if with_anti_detect:
        hooks.on_pre_execute(create_anti_detect_hook())

    return ScriptRunner(
        nodes=nodes,
        start_node_id=start_node_id,
        hooks=hooks,
        on_error=on_error,
        max_retries=max_retries,
    )
