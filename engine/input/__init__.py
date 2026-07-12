"""输入模拟模块 — 键盘和鼠标的底层操作能力

提供 KeyboardController 和 MouseController 两个核心类，
为键鼠节点提供统一的输入模拟接口。

使用示例:
    from engine.input import KeyboardController, MouseController, MoveSpeed

    kb = KeyboardController()
    kb.key_press("a")
    kb.key_combo(["ctrl", "c"])

    mouse = MouseController(speed=MoveSpeed.HUMAN_LIKE)
    mouse.mouse_click(100, 200)
"""

from engine.input.keyboard import (
    KeyboardController,
    KeyboardException,
    KeyMap,
    OpResult,
)
from engine.input.mouse import (
    MouseController,
    MouseException,
    MoveSpeed,
    BezierPath,
)

__all__ = [
    # 键盘
    "KeyboardController",
    "KeyboardException",
    "KeyMap",
    "OpResult",
    # 鼠标
    "MouseController",
    "MouseException",
    "MoveSpeed",
    "BezierPath",
]
