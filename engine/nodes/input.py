"""输入模拟节点 — 键盘和鼠标操作"""

import asyncio
from engine.nodes.base import BaseNode, NodeResult, NodeStatus


class KeyPressNode(BaseNode):
    """按键按下节点 — 按下并释放单个按键"""
    node_type = "key_press"

    async def execute(self, ctx) -> NodeResult:
        key = self.config.get("key", "")
        ctx.info(f"按键: {key}", self.node_id)
        await asyncio.sleep(0.01)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return bool(self.config.get("key"))


class KeyComboNode(BaseNode):
    """组合键节点 — 同时按下多个键（如 Ctrl+C）"""
    node_type = "key_combo"

    async def execute(self, ctx) -> NodeResult:
        keys = self.config.get("keys", [])
        ctx.info(f"组合键: {'+'.join(keys)}", self.node_id)
        await asyncio.sleep(0.02)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        keys = self.config.get("keys", [])
        return isinstance(keys, list) and len(keys) >= 1


class KeyHoldNode(BaseNode):
    """按键按住节点 — 按住按键指定时长后释放"""
    node_type = "key_hold"

    async def execute(self, ctx) -> NodeResult:
        key = self.config.get("key", "")
        duration = float(self.config.get("duration", 0.5))
        ctx.info(f"按住 {key} {duration}s", self.node_id)
        await asyncio.sleep(min(duration, 10.0))
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        key = self.config.get("key", "")
        duration = self.config.get("duration", 0)
        return bool(key) and isinstance(duration, (int, float)) and duration >= 0


class MouseMoveNode(BaseNode):
    """鼠标移动节点 — 移动到指定坐标"""
    node_type = "mouse_move"

    async def execute(self, ctx) -> NodeResult:
        x = int(self.config.get("x", 0))
        y = int(self.config.get("y", 0))
        ctx.info(f"鼠标移动到 ({x}, {y})", self.node_id)
        await asyncio.sleep(0.01)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return "x" in self.config and "y" in self.config


class MouseClickNode(BaseNode):
    """鼠标点击节点 — 在指定坐标或当前位置左键点击"""
    node_type = "mouse_click"

    async def execute(self, ctx) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.info(f"鼠标点击 {pos}", self.node_id)
        await asyncio.sleep(0.02)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return True


class MouseDblClickNode(BaseNode):
    """鼠标双击节点"""
    node_type = "mouse_dblclick"

    async def execute(self, ctx) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.info(f"鼠标双击 {pos}", self.node_id)
        await asyncio.sleep(0.05)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return True


class MouseRightNode(BaseNode):
    """鼠标右键节点"""
    node_type = "mouse_right"

    async def execute(self, ctx) -> NodeResult:
        x = self.config.get("x")
        y = self.config.get("y")
        pos = f"({x}, {y})" if x is not None and y is not None else "当前位置"
        ctx.info(f"鼠标右键 {pos}", self.node_id)
        await asyncio.sleep(0.02)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return True


class MouseDragNode(BaseNode):
    """鼠标拖拽节点 — 从起点拖到终点"""
    node_type = "mouse_drag"

    async def execute(self, ctx) -> NodeResult:
        from_x = int(self.config.get("from_x", 0))
        from_y = int(self.config.get("from_y", 0))
        to_x = int(self.config.get("to_x", 0))
        to_y = int(self.config.get("to_y", 0))
        duration = float(self.config.get("duration", 0.3))
        ctx.info(f"鼠标拖拽 ({from_x},{from_y}) -> ({to_x},{to_y})", self.node_id)
        await asyncio.sleep(min(duration, 5.0))
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        return all(k in self.config for k in ("from_x", "from_y", "to_x", "to_y"))


class MouseScrollNode(BaseNode):
    """鼠标滚轮节点 — 向上或向下滚动"""
    node_type = "mouse_scroll"

    async def execute(self, ctx) -> NodeResult:
        direction = self.config.get("direction", "down")
        amount = int(self.config.get("amount", 3))
        ctx.info(f"鼠标滚轮 {direction} x{amount}", self.node_id)
        await asyncio.sleep(0.03)
        return NodeResult(status=NodeStatus.SUCCESS)

    def validate(self) -> bool:
        direction = self.config.get("direction", "down")
        return direction in ("up", "down")
