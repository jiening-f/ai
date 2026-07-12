"""
鼠标操作节点

- MouseClickNode: 左键单击
- MouseDblClickNode: 左键双击
- MouseRightNode: 右键单击
- MouseDragNode: 拖拽
- MouseScrollNode: 滚轮滚动
"""

from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class MouseClickNode(BaseNode):
    """鼠标左键单击节点"""

    node_type = "mouse_click"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x", 0)
        y = self.config.get("y", 0)
        relative = self.config.get("relative", False)

        ctx.log(f"[鼠标] 单击 ({x}, {y})" + (" 相对坐标" if relative else ""))

        mouse = ctx.get_service("mouse")
        if mouse:
            mouse.mouse_click(x, y, relative=relative)
        else:
            ctx.log("[鼠标] 警告: 鼠标服务未注册")

        return NodeResult(success=True)

    def validate(self) -> bool:
        return True

    @classmethod
    def default_config(cls) -> dict:
        return {"x": 0, "y": 0, "relative": False}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "鼠标单击",
            "category": "鼠标",
            "description": "在指定坐标执行鼠标左键单击",
            "config_schema": {
                "x": {"type": "number", "default": 0, "description": "X 坐标"},
                "y": {"type": "number", "default": 0, "description": "Y 坐标"},
                "relative": {"type": "boolean", "default": False, "description": "是否相对于当前窗口"},
            },
        }


class MouseDblClickNode(BaseNode):
    """鼠标左键双击节点"""

    node_type = "mouse_dblclick"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x", 0)
        y = self.config.get("y", 0)
        ctx.log(f"[鼠标] 双击 ({x}, {y})")

        mouse = ctx.get_service("mouse")
        if mouse:
            mouse.mouse_dblclick(x, y)
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"x": 0, "y": 0}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "鼠标双击",
            "category": "鼠标",
            "description": "在指定坐标执行鼠标左键双击",
            "config_schema": {
                "x": {"type": "number", "default": 0},
                "y": {"type": "number", "default": 0},
            },
        }


class MouseRightNode(BaseNode):
    """鼠标右键单击节点"""

    node_type = "mouse_right"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x = self.config.get("x", 0)
        y = self.config.get("y", 0)
        ctx.log(f"[鼠标] 右键 ({x}, {y})")

        mouse = ctx.get_service("mouse")
        if mouse:
            mouse.mouse_right(x, y)
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"x": 0, "y": 0}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "鼠标右键",
            "category": "鼠标",
            "description": "在指定坐标执行鼠标右键单击",
            "config_schema": {"x": {"type": "number", "default": 0}, "y": {"type": "number", "default": 0}},
        }


class MouseDragNode(BaseNode):
    """鼠标拖拽节点"""

    node_type = "mouse_drag"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        x1 = self.config.get("x1", 0)
        y1 = self.config.get("y1", 0)
        x2 = self.config.get("x2", 0)
        y2 = self.config.get("y2", 0)
        duration_ms = self.config.get("duration_ms", 500)

        ctx.log(f"[鼠标] 拖拽 ({x1},{y1}) → ({x2},{y2}) {duration_ms}ms")

        mouse = ctx.get_service("mouse")
        if mouse:
            mouse.mouse_drag(x1, y1, x2, y2, duration_ms)
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"x1": 0, "y1": 0, "x2": 100, "y2": 100, "duration_ms": 500}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "鼠标拖拽",
            "category": "鼠标",
            "description": "从起点拖拽鼠标到终点",
            "config_schema": {
                "x1": {"type": "number", "default": 0},
                "y1": {"type": "number", "default": 0},
                "x2": {"type": "number", "default": 100},
                "y2": {"type": "number", "default": 100},
                "duration_ms": {"type": "number", "default": 500},
            },
        }


class MouseScrollNode(BaseNode):
    """鼠标滚轮滚动节点"""

    node_type = "mouse_scroll"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        clicks = self.config.get("clicks", 3)
        x = self.config.get("x")
        y = self.config.get("y")

        ctx.log(f"[鼠标] 滚轮 {'上' if clicks > 0 else '下'} {abs(clicks)} 格")

        mouse = ctx.get_service("mouse")
        if mouse:
            mouse.mouse_scroll(clicks, x, y)
        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"clicks": 3, "x": None, "y": None}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "鼠标滚轮",
            "category": "鼠标",
            "description": "滚动鼠标滚轮，正数向上，负数向下",
            "config_schema": {
                "clicks": {"type": "number", "default": 3, "description": "滚动格数，正上负下"},
                "x": {"type": "number", "default": None, "description": "可选，滚动前先移动到的 X"},
                "y": {"type": "number", "default": None, "description": "可选，滚动前先移动到的 Y"},
            },
        }
