"""鼠标操作节点：move, click, dblclick, right_click, drag, scroll。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class MouseMoveNode(BaseNode):
    """鼠标移动 —— 将鼠标移动到指定坐标。"""
    node_type = "mouse_move"
    node_category = "鼠标"
    node_description = "移动鼠标到指定绝对坐标或相对偏移"
    default_config = {"x": 0, "y": 0, "mode": "absolute", "duration_ms": 200}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x", 0)
        y = self.config.get("y", 0)
        mode = self.config.get("mode", "absolute")
        duration = self.config.get("duration_ms", 200)
        ctx.log(f"[mouse_move] {mode} 移动到 ({x}, {y}) 持续 {duration}ms")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"x": x, "y": y, "mode": mode, "action": "move", "duration_ms": duration},
        )

    def validate(self) -> bool:
        mode = self.config.get("mode", "absolute")
        return mode in ("absolute", "relative")


class MouseClickNode(BaseNode):
    """鼠标左键单击。"""
    node_type = "mouse_click"
    node_category = "鼠标"
    node_description = "鼠标左键单击指定坐标或当前鼠标位置"
    default_config = {"x": None, "y": None, "button": "left"}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.log(f"[mouse_click] 左键单击 {pos}")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"x": x, "y": y, "action": "click", "button": "left"},
        )


class MouseDblClickNode(BaseNode):
    """鼠标左键双击。"""
    node_type = "mouse_dblclick"
    node_category = "鼠标"
    node_description = "鼠标左键双击指定坐标"
    default_config = {"x": None, "y": None, "interval_ms": 100}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        interval = self.config.get("interval_ms", 100)
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.log(f"[mouse_dblclick] 左键双击 {pos}")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"x": x, "y": y, "action": "dblclick", "interval_ms": interval},
        )


class MouseRightClickNode(BaseNode):
    """鼠标右键单击。"""
    node_type = "mouse_right"
    node_category = "鼠标"
    node_description = "鼠标右键单击指定坐标"
    default_config = {"x": None, "y": None}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.log(f"[mouse_right] 右键单击 {pos}")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"x": x, "y": y, "action": "right_click", "button": "right"},
        )


class MouseDragNode(BaseNode):
    """鼠标拖拽。"""
    node_type = "mouse_drag"
    node_category = "鼠标"
    node_description = "从起点拖拽鼠标到终点"
    default_config = {"from_x": 0, "from_y": 0, "to_x": 100, "to_y": 100, "duration_ms": 500}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        fx = self.config.get("from_x", 0)
        fy = self.config.get("from_y", 0)
        tx = self.config.get("to_x", 100)
        ty = self.config.get("to_y", 100)
        duration = self.config.get("duration_ms", 500)
        ctx.log(f"[mouse_drag] 拖拽 ({fx},{fy}) → ({tx},{ty}) 持续 {duration}ms")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={
                "from": {"x": fx, "y": fy},
                "to": {"x": tx, "y": ty},
                "action": "drag",
                "duration_ms": duration,
            },
        )

    def validate(self) -> bool:
        for key in ("from_x", "from_y", "to_x", "to_y"):
            if not isinstance(self.config.get(key), (int, float)):
                return False
        return True


class MouseScrollNode(BaseNode):
    """鼠标滚轮滚动。"""
    node_type = "mouse_scroll"
    node_category = "鼠标"
    node_description = "鼠标滚轮滚动指定距离"
    default_config = {"x": None, "y": None, "scroll_x": 0, "scroll_y": -120}

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        sx = self.config.get("scroll_x", 0)
        sy = self.config.get("scroll_y", -120)
        ctx.log(f"[mouse_scroll] 滚轮 ({sx}, {sy})")
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"scroll_x": sx, "scroll_y": sy, "action": "scroll"},
        )
