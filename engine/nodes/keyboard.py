"""键盘输入节点：key_press, key_combo, key_hold。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class KeyPressNode(BaseNode):
    """单键按下/释放节点。"""
    node_type = "key_press"
    node_category = "键盘"
    node_description = "按下并释放指定按键"
    default_config = {"key": "a", "duration_ms": 50}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        key = self.config.get("key", "a")
        duration = self.config.get("duration_ms", 50)
        ctx.log(f"[key_press] 按键 {key} (持续 {duration}ms)")
        # 实际输入由 input 子系统执行
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"key": key, "action": "press", "duration_ms": duration},
        )

    def validate(self) -> bool:
        key = self.config.get("key", "")
        return isinstance(key, str) and len(key) > 0


class KeyComboNode(BaseNode):
    """组合键节点（如 Ctrl+C）。"""
    node_type = "key_combo"
    node_category = "键盘"
    node_description = "同时按下多个按键（组合键）"
    default_config = {"keys": ["ctrl", "c"], "duration_ms": 100}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        keys = self.config.get("keys", [])
        duration = self.config.get("duration_ms", 100)
        combo = "+".join(keys)
        ctx.log(f"[key_combo] 组合键 {combo} (持续 {duration}ms)")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"keys": keys, "action": "combo", "duration_ms": duration},
        )

    def validate(self) -> bool:
        keys = self.config.get("keys", [])
        return isinstance(keys, list) and len(keys) >= 2


class KeyHoldNode(BaseNode):
    """长按节点 —— 按住按键指定时长后释放。"""
    node_type = "key_hold"
    node_category = "键盘"
    node_description = "按住按键指定时长后释放"
    default_config = {"key": "w", "hold_ms": 2000}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        key = self.config.get("key", "w")
        hold_ms = self.config.get("hold_ms", 2000)
        ctx.log(f"[key_hold] 长按 {key} (持续 {hold_ms}ms)")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"key": key, "action": "hold", "hold_ms": hold_ms},
        )

    def validate(self) -> bool:
        key = self.config.get("key", "")
        hold_ms = self.config.get("hold_ms", 0)
        return isinstance(key, str) and len(key) > 0 and isinstance(hold_ms, (int, float)) and hold_ms > 0
