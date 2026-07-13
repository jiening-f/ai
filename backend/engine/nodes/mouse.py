"""鼠标节点 — mouse_click, mouse_dblclick, mouse_right, mouse_drag, mouse_scroll, mouse_move"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import register_node

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


# ── 鼠标执行函数（后期可注入不同实现） ──

def _click(x: int, y: int, button: str = "left") -> None:
    """默认鼠标点击 — 使用 pyautogui"""
    try:
        import pyautogui
        pyautogui.click(x, y, button=button)
    except Exception:
        pass


def _dblclick(x: int, y: int) -> None:
    try:
        import pyautogui
        pyautogui.doubleClick(x, y)
    except Exception:
        pass


def _right_click(x: int, y: int) -> None:
    try:
        import pyautogui
        pyautogui.rightClick(x, y)
    except Exception:
        pass


def _drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float) -> None:
    try:
        import pyautogui
        pyautogui.moveTo(from_x, from_y)
        pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration)
    except Exception:
        pass


def _scroll(direction: str, amount: int, x: int | None, y: int | None) -> None:
    try:
        import pyautogui
        if x is not None and y is not None:
            pyautogui.moveTo(x, y)
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks)
    except Exception:
        pass


def _move(x: int, y: int, duration: float = 0.0) -> None:
    """移动鼠标到指定位置（不点击）"""
    try:
        import pyautogui
        pyautogui.moveTo(x, y, duration=duration)
    except Exception:
        pass


@register_node("mouse_click", "鼠标", "鼠标左键点击", "在指定坐标执行鼠标左键点击")
class MouseClickNode(BaseNode):
    """鼠标左键点击节点

    Config:
        x: 目标 X 坐标（支持变量，如 "$target_x"）
        y: 目标 Y 坐标（支持变量，如 "$target_y"）
        button: 鼠标按键（"left" / "right" / "middle"，默认 "left"）
    """
    default_config = {"x": ..., "y": ..., "button": "left"}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        x = self._resolve_coord("x", ctx)
        y = self._resolve_coord("y", ctx)
        button = str(self.config.get("button", "left"))
        if x is None or y is None:
            return NodeResult.fail("未指定点击坐标")
        ctx.log(f"🖱 点击: ({x}, {y}) {button}")
        _click(x, y, button)
        return NodeResult.ok(x=x, y=y)

    def _resolve_coord(self, key: str, ctx: "ExecutionContext") -> int | None:
        val = self.config.get(key)
        if val is None:
            return None
        if isinstance(val, str) and str(val).startswith("$"):
            return ctx.get_var(str(val)[1:])
        return int(val)

    def validate(self) -> bool:
        x, y = self.config.get("x"), self.config.get("y")
        return x is not None and y is not None


@register_node("mouse_dblclick", "鼠标", "鼠标左键双击", "在指定坐标执行鼠标左键双击")
class MouseDblClickNode(BaseNode):
    """鼠标双击节点

    Config:
        x: 目标 X 坐标
        y: 目标 Y 坐标
    """
    default_config = {"x": ..., "y": ...}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        x = int(self.config.get("x", 0))
        y = int(self.config.get("y", 0))
        ctx.log(f"🖱 双击: ({x}, {y})")
        _dblclick(x, y)
        return NodeResult.ok(x=x, y=y)

    def validate(self) -> bool:
        return self.config.get("x") is not None and self.config.get("y") is not None


@register_node("mouse_right", "鼠标", "鼠标右键点击", "在指定坐标执行鼠标右键点击")
class MouseRightClickNode(BaseNode):
    """鼠标右键点击节点

    Config:
        x: 目标 X 坐标
        y: 目标 Y 坐标
    """
    default_config = {"x": ..., "y": ...}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        x = int(self.config.get("x", 0))
        y = int(self.config.get("y", 0))
        ctx.log(f"🖱 右键点击: ({x}, {y})")
        _right_click(x, y)
        return NodeResult.ok(x=x, y=y)

    def validate(self) -> bool:
        return self.config.get("x") is not None and self.config.get("y") is not None


@register_node("mouse_drag", "鼠标", "鼠标拖拽", "从起点拖拽到终点")
class MouseDragNode(BaseNode):
    """鼠标拖拽节点

    Config:
        from_x: 起始 X 坐标
        from_y: 起始 Y 坐标
        to_x: 终点 X 坐标
        to_y: 终点 Y 坐标
        duration: 拖拽时长，单位秒（默认 0.5）
    """
    default_config = {"from_x": ..., "from_y": ..., "to_x": ..., "to_y": ..., "duration": 0.5}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        fx = int(self.config.get("from_x", 0))
        fy = int(self.config.get("from_y", 0))
        tx = int(self.config.get("to_x", 0))
        ty = int(self.config.get("to_y", 0))
        duration = float(self.config.get("duration", 0.5))
        ctx.log(f"🖱 拖拽: ({fx}, {fy}) → ({tx}, {ty}) {duration:.1f}s")
        _drag(fx, fy, tx, ty, duration)
        return NodeResult.ok(from_x=fx, from_y=fy, to_x=tx, to_y=ty)

    def validate(self) -> bool:
        for key in ("from_x", "from_y", "to_x", "to_y"):
            if self.config.get(key) is None:
                return False
        return True


@register_node("mouse_scroll", "鼠标", "鼠标滚轮", "在指定位置滚动鼠标滚轮")
class MouseScrollNode(BaseNode):
    """鼠标滚轮节点

    Config:
        direction: 滚动方向（"up" / "down"）
        amount: 滚动量（格数，默认 3）
        x: 可选，滚动时鼠标所在 X 坐标
        y: 可选，滚动时鼠标所在 Y 坐标
    """
    default_config = {"direction": "down", "amount": 3, "x": None, "y": None}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        direction = str(self.config.get("direction", "down"))
        amount = int(self.config.get("amount", 3))
        x = self.config.get("x")
        y = self.config.get("y")
        x = int(x) if x is not None else None
        y = int(y) if y is not None else None
        ctx.log(f"🖱 滚轮: {direction} ×{amount}" + (f" at ({x}, {y})" if x is not None else ""))
        _scroll(direction, amount, x, y)
        return NodeResult.ok(direction=direction, amount=amount)

    def validate(self) -> bool:
        direction = self.config.get("direction", "")
        amount = self.config.get("amount", 0)
        return direction in ("up", "down") and isinstance(amount, (int, float)) and amount > 0


@register_node("mouse_move", "鼠标", "鼠标移动", "移动鼠标到指定坐标（不点击）")
class MouseMoveNode(BaseNode):
    """鼠标移动节点 — 将光标移动到指定位置

    Config:
        x: 目标 X 坐标
        y: 目标 Y 坐标
        duration: 移动耗时，单位秒（默认 0，瞬间移动）
    """
    default_config = {"x": ..., "y": ..., "duration": 0.0}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        x = int(self.config.get("x", 0))
        y = int(self.config.get("y", 0))
        duration = float(self.config.get("duration", 0.0))
        ctx.log(f"🖱 移动: ({x}, {y})" + (f" {duration:.1f}s" if duration > 0 else ""))
        _move(x, y, duration)
        return NodeResult.ok(x=x, y=y)

    def validate(self) -> bool:
        return self.config.get("x") is not None and self.config.get("y") is not None
