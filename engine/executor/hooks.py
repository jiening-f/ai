"""
钩子系统

支持在脚本执行生命周期的关键节点插入自定义逻辑。

预定义钩子：
- pre_execute: 节点执行前调用
- post_execute: 节点执行后调用
- on_pause: 暂停时调用
- on_resume: 恢复时调用
- on_stop: 停止时调用
- on_error: 出错时调用
- on_complete: 脚本完成时调用

用法:
    hooks = HookManager()
    hooks.register("post_execute", lambda ctx, node, result: print(f"{node.node_id} done"))
"""

from typing import Callable, Any
from engine.executor.context import ExecutionContext
from engine.nodes.base import BaseNode, NodeResult


# 钩子回调类型
HookCallback = Callable[..., Any]


class HookManager:
    """钩子管理器：注册和触发生命周期钩子"""

    # 支持的钩子名称
    HOOK_NAMES = [
        "pre_execute",   # (ctx: ExecutionContext, node: BaseNode)
        "post_execute",  # (ctx: ExecutionContext, node: BaseNode, result: NodeResult)
        "on_pause",      # (ctx: ExecutionContext)
        "on_resume",     # (ctx: ExecutionContext)
        "on_stop",       # (ctx: ExecutionContext)
        "on_error",      # (ctx: ExecutionContext, node: BaseNode, error: Exception)
        "on_complete",   # (ctx: ExecutionContext)
    ]

    def __init__(self):
        self._hooks: dict[str, list[HookCallback]] = {name: [] for name in self.HOOK_NAMES}

    def register(self, hook_name: str, callback: HookCallback):
        """
        注册一个钩子回调

        Args:
            hook_name: 钩子名称（必须是 HOOK_NAMES 之一）
            callback: 回调函数

        Raises:
            ValueError: 无效的钩子名称
        """
        if hook_name not in self.HOOK_NAMES:
            raise ValueError(f"无效的钩子名称: {hook_name}，支持: {self.HOOK_NAMES}")
        self._hooks[hook_name].append(callback)

    def unregister(self, hook_name: str, callback: HookCallback):
        """取消注册某个钩子回调"""
        if hook_name in self._hooks:
            self._hooks[hook_name] = [cb for cb in self._hooks[hook_name] if cb is not callback]

    async def trigger(self, hook_name: str, *args):
        """
        触发一个钩子的所有回调

        Args:
            hook_name: 钩子名称
            *args: 传递给回调的参数
        """
        if hook_name not in self._hooks:
            return
        for callback in self._hooks[hook_name]:
            try:
                if hasattr(callback, "__call__"):
                    result = callback(*args)
                    # 支持异步回调
                    if hasattr(result, "__await__"):
                        await result
            except Exception as e:
                # 钩子自身异常不中断主流程
                import traceback
                traceback.print_exc()
