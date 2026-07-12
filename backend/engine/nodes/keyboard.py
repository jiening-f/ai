"""键盘节点 — key_press, key_combo, key_hold"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import register_node

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


# ── 按键执行方式（后期可注入不同实现） ──
def _press_key(key: str) -> None:
    """默认按键实现 — 使用 pyautogui"""
    try:
        import pyautogui
        pyautogui.press(key)
    except Exception:
        pass


def _key_down(key: str) -> None:
    try:
        import pyautogui
        pyautogui.keyDown(key)
    except Exception:
        pass


def _key_up(key: str) -> None:
    try:
        import pyautogui
        pyautogui.keyUp(key)
    except Exception:
        pass


def _hotkey(*keys: str) -> None:
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
    except Exception:
        pass


@register_node("key_press", "键盘", "按键", "按下并释放指定按键")
class KeyPressNode(BaseNode):
    """按键节点 — 按下并立即释放一个键

    Config:
        key: 按键名称（如 "a", "enter", "space", "f1"）
    """
    default_config = {"key": ...}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        key = str(self.config.get("key", ""))
        if not key:
            return NodeResult.fail("未指定按键")
        ctx.log(f"⌨ 按键: {key}")
        _press_key(key)
        return NodeResult.ok()

    def validate(self) -> bool:
        key = self.config.get("key")
        return key is not None and str(key).strip() != ""


@register_node("key_combo", "键盘", "组合键", "同时按下多个键（如 Ctrl+C）")
class KeyComboNode(BaseNode):
    """组合键节点 — 模拟组合键（如 Ctrl+C, Alt+F4）

    Config:
        keys: 按键列表，按顺序同时按下（如 ["ctrl", "c"]）
    """
    default_config = {"keys": ...}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        keys = self.config.get("keys", [])
        if not keys:
            return NodeResult.fail("未指定组合键")
        key_str = "+".join(str(k) for k in keys)
        ctx.log(f"⌨ 组合键: {key_str}")
        _hotkey(*[str(k) for k in keys])
        return NodeResult.ok()

    def validate(self) -> bool:
        keys = self.config.get("keys")
        return isinstance(keys, list) and len(keys) >= 1


@register_node("key_hold", "键盘", "长按", "按住指定按键一段时间后释放")
class KeyHoldNode(BaseNode):
    """长按节点 — 按住按键持续指定时长

    Config:
        key: 按键名称
        duration: 按住时长，单位秒（默认 0.5）
    """
    default_config = {"key": ..., "duration": 0.5}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        key = str(self.config.get("key", ""))
        duration = float(self.config.get("duration", 0.5))
        if not key:
            return NodeResult.fail("未指定按键")
        ctx.log(f"⌨ 长按: {key} ({duration:.1f}s)")
        _key_down(key)
        await asyncio.sleep(duration)
        _key_up(key)
        return NodeResult.ok()

    def validate(self) -> bool:
        key = self.config.get("key")
        duration = self.config.get("duration", 0)
        return key is not None and str(key).strip() != "" and isinstance(duration, (int, float)) and duration >= 0
