"""
执行循环与状态机

异步脚本执行引擎，负责遍历节点图、调度节点执行、管理状态切换。

核心能力：
- 从 start 节点开始，按 next_nodes 遍历图
- 支持条件分支（condition 节点改变 next_node_id）
- 支持循环（loop 节点跳转到指定节点）
- 暂停/恢复/停止/单步调试
- 钩子触发（pre_execute / post_execute）
- 异常处理（on_error 配置: stop / continue / retry）
"""

import asyncio
import time
from engine.executor.context import ExecutionContext, ExecutionStatus
from engine.executor.hooks import HookManager
from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import get_node_class


class ScriptRunner:
    """
    脚本执行器

    用法:
        runner = ScriptRunner(ctx, node_map, hook_manager)
        await runner.run()
    """

    def __init__(
        self,
        ctx: ExecutionContext,
        node_map: dict[str, dict],  # node_id → {type, config, next_nodes, condition}
        hooks: HookManager | None = None,
    ):
        self.ctx = ctx
        self.node_map = node_map
        self.hooks = hooks or HookManager()

        # 找到开始节点
        self._start_node_id: str = self._find_start_node()
        self._current_node_id: str = ""

        # 单步标记
        self._step_mode: bool = False
        self._step_event: asyncio.Event | None = None

    def _find_start_node(self) -> str:
        """找到 node_type == 'start' 的节点"""
        for nid, nd in self.node_map.items():
            if nd.get("type") == "start":
                return nid
        # 取第一个节点作为默认起始
        if self.node_map:
            return next(iter(self.node_map))
        raise ValueError("节点图为空，找不到起始节点")

    def _instantiate_node(self, node_id: str) -> BaseNode | None:
        """根据节点配置实例化节点对象"""
        node_def = self.node_map.get(node_id)
        if not node_def:
            return None

        node_type = node_def.get("type", "")
        node_cls = get_node_class(node_type)
        if not node_cls:
            self.ctx.log(f"[错误] 未知节点类型: {node_type}", "ERROR")
            return None

        return node_cls(
            node_id=node_id,
            config=node_def.get("config", {}),
            next_nodes=node_def.get("next_nodes", []),
            condition=node_def.get("condition"),
        )

    def _get_next_node_id(self, node: BaseNode, result: NodeResult) -> str | None:
        """确定下一个要执行的节点 ID"""
        # 结果中指定了 next_node_id（条件分支/循环跳转）
        if result.next_node_id:
            return result.next_node_id

        # 默认取 next_nodes 的第一个
        if node.next_nodes:
            return node.next_nodes[0]
        return None

    async def run(self) -> bool:
        """
        执行完整的脚本流程

        Returns:
            bool: True 表示成功完成，False 表示因错误或停止而中断
        """
        self.ctx.status = ExecutionStatus.RUNNING
        self.ctx.start_timer()
        self._current_node_id = self._start_node_id

        await self.hooks.trigger("pre_execute", self.ctx, None)

        visited = set()
        max_iterations = 10000  # 安全上限

        try:
            for _ in range(max_iterations):
                # 检查是否应该停止
                if self.ctx.should_stop():
                    self.ctx.log(f"[引擎] 执行已停止 (状态: {self.ctx.status.value})")
                    break

                # 检查是否暂停
                if self.ctx.is_paused():
                    await self.hooks.trigger("on_pause", self.ctx)
                    # 等待恢复
                    while self.ctx.is_paused() and not self.ctx.should_stop():
                        await asyncio.sleep(0.1)
                    if self.ctx.should_stop():
                        break
                    await self.hooks.trigger("on_resume", self.ctx)

                # 获取下一个要执行的节点
                node_id = self._current_node_id
                if not node_id:
                    # 没有下一个节点 → 正常结束
                    self.ctx.log("[引擎] 流程结束（无后续节点）")
                    self.ctx.status = ExecutionStatus.COMPLETED
                    break

                # 防止无限循环
                if node_id in visited:
                    self.ctx.log(f"[引擎] 检测到循环回访节点 {node_id}")
                visited.add(node_id)

                self.ctx.current_node_id = node_id
                node = self._instantiate_node(node_id)
                if not node:
                    self.ctx.log(f"[引擎] 节点 {node_id} 实例化失败，跳过")
                    break

                # pre_execute 钩子
                await self.hooks.trigger("pre_execute", self.ctx, node)

                # 执行节点
                start_time = time.time()
                try:
                    result = await node.execute(self.ctx)
                except Exception as e:
                    # 错误处理
                    error_policy = node.config.get("on_error", "stop")
                    self.ctx.log(f"[错误] 节点 {node_id} 执行异常: {e}", "ERROR")
                    await self.hooks.trigger("on_error", self.ctx, node, e)

                    if error_policy == "retry":
                        retries = node.config.get("retry_count", 1)
                        retried = 0
                        for _ in range(retries):
                            try:
                                result = await node.execute(self.ctx)
                                break
                            except Exception:
                                retried += 1
                        if retried >= retries:
                            result = NodeResult(success=False, error_message=str(e))
                    elif error_policy == "continue":
                        result = NodeResult(success=False, error_message=str(e))
                    else:  # stop
                        self.ctx.status = ExecutionStatus.ERROR
                        result = NodeResult(success=False, error_message=str(e))

                elapsed = (time.time() - start_time) * 1000
                self.ctx.increment_node_count()
                self.ctx.log(f"[引擎] 节点 {node_id} 完成 ({elapsed:.1f}ms)")

                # post_execute 钩子
                await self.hooks.trigger("post_execute", self.ctx, node, result)

                # 检查执行结果
                if not result.success and self.ctx.status == ExecutionStatus.ERROR:
                    break

                # 确定下一个节点
                next_id = self._get_next_node_id(node, result)
                self._current_node_id = next_id or ""

                # 单步模式：执行一个节点后暂停
                if self._step_mode:
                    self.ctx.status = ExecutionStatus.PAUSED
                    if self._step_event:
                        self._step_event.set()

                # end 节点：标记完成
                if node.node_type == "end":
                    self.ctx.status = ExecutionStatus.COMPLETED
                    break

        except Exception as e:
            self.ctx.log(f"[引擎] 致命错误: {e}", "ERROR")
            self.ctx.status = ExecutionStatus.ERROR
            return False

        # 如果正常完成
        if self.ctx.status == ExecutionStatus.RUNNING:
            self.ctx.status = ExecutionStatus.COMPLETED

        if self.ctx.status == ExecutionStatus.COMPLETED:
            await self.hooks.trigger("on_complete", self.ctx)
        elif self.ctx.status == ExecutionStatus.ERROR:
            await self.hooks.trigger("on_error", self.ctx, None, None)
        elif self.ctx.status == ExecutionStatus.STOPPED:
            await self.hooks.trigger("on_stop", self.ctx)

        elapsed = self.ctx.elapsed_ms
        self.ctx.log(f"[引擎] 执行完毕 (状态: {self.ctx.status.value}, 耗时: {elapsed:.1f}ms, 节点数: {self.ctx.node_count})")
        return self.ctx.status == ExecutionStatus.COMPLETED

    # ── 状态控制 ──────────────────────

    def pause(self):
        """暂停执行（当前节点完成后暂停）"""
        self.ctx.log("[引擎] 收到暂停请求")
        self.ctx.status = ExecutionStatus.PAUSED

    def resume(self):
        """从暂停恢复"""
        self.ctx.log("[引擎] 收到恢复请求")
        if self.ctx.is_paused():
            self.ctx.status = ExecutionStatus.RUNNING

    def stop(self):
        """立即停止执行"""
        self.ctx.log("[引擎] 收到停止请求")
        self.ctx.status = ExecutionStatus.STOPPED

    async def step(self) -> bool:
        """
        单步调试：执行一个节点后自动暂停

        Returns:
            bool: True 表示还有后续节点，False 表示流程结束
        """
        self._step_mode = True
        self._step_event = asyncio.Event()
        if self.ctx.status != ExecutionStatus.RUNNING:
            self.ctx.status = ExecutionStatus.RUNNING
            if not self.ctx.has_started:
                self.ctx.start_timer()
            if not self._current_node_id:
                self._current_node_id = self._start_node_id

        # 在 run() 循环中执行单个节点，然后等待
        await asyncio.wait_for(self._step_event.wait(), timeout=60.0)
        self._step_event.clear()

        return bool(self._current_node_id and self.ctx.status not in (
            ExecutionStatus.COMPLETED, ExecutionStatus.ERROR, ExecutionStatus.STOPPED
        ))

    def is_running(self) -> bool:
        return self.ctx.is_running()

    def is_paused(self) -> bool:
        return self.ctx.is_paused()

    def is_stopped(self) -> bool:
        """已停止（停止或错误状态）"""
        return self.ctx.should_stop()


async def create_test_flow() -> dict[str, dict]:
    """
    创建一个5节点测试流程，用于验证执行器

    流程: start → variable_set → wait(500ms) → condition → text_output → end
    """
    return {
        "n1": {"type": "start", "config": {}, "next_nodes": ["n2"], "condition": None},
        "n2": {"type": "variable_set", "config": {"var_name": "count", "var_value": "1"}, "next_nodes": ["n3"], "condition": None},
        "n3": {"type": "wait", "config": {"duration_ms": 500}, "next_nodes": ["n4"], "condition": None},
        "n4": {"type": "condition", "config": {}, "next_nodes": ["n5", "n5"], "condition": "$count == '1'"},
        "n5": {"type": "text_output", "config": {"text": "测试完成，count=$count"}, "next_nodes": ["n6"], "condition": None},
        "n6": {"type": "end", "config": {}, "next_nodes": [], "condition": None},
    }
