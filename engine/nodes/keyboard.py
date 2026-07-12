"""
键盘操作节点

- KeyPressNode: 单键按下+释放
- KeyComboNode: 组合键（如 Ctrl+C）
- KeyHoldNode: 长按指定时长
"""

from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class KeyPressNode(BaseNode):
    """单键按下节点"""

    node_type = "key_press"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        key = self.config.get("key", "")
        if not key:
            return NodeResult(success=False, error_message="未指定按键")

        ctx.log(f"[按键] 按下 {key}")

        # 使用输入模拟模块（通过上下文获取）
        keyboard = ctx.get_service("keyboard")
        if keyboard:
            keyboard.key_press(key)
        else:
            ctx.log("[按键] 警告: 键盘服务未注册")

        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("key"))

    @classmethod
    def default_config(cls) -> dict:
        return {"key": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "按键",
            "category": "键盘",
            "description": "模拟按下并释放一个按键",
            "config_schema": {"key": {"type": "string", "default": "", "description": "按键名称，如 a/b/enter/tab/space"}},
        }


class KeyComboNode(BaseNode):
    """组合键节点"""

    node_type = "key_combo"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        keys = self.config.get("keys", [])
        if not keys:
            return NodeResult(success=False, error_message="未指定组合键")

        ctx.log(f"[组合键] 按下 {'+'.join(keys)}")

        keyboard = ctx.get_service("keyboard")
        if keyboard:
            keyboard.key_combo(keys)
        else:
            ctx.log("[组合键] 警告: 键盘服务未注册")

        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("keys"))

    @classmethod
    def default_config(cls) -> dict:
        return {"keys": []}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "组合键",
            "category": "键盘",
            "description": "模拟按下组合键，如 Ctrl+C、Alt+Tab",
            "config_schema": {"keys": {"type": "array", "items": "string", "default": [], "description": "按键列表"}},
        }


class KeyHoldNode(BaseNode):
    """长按节点"""

    node_type = "key_hold"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        key = self.config.get("key", "")
        duration_ms = self.config.get("duration_ms", 500)
        if not key:
            return NodeResult(success=False, error_message="未指定按键")

        ctx.log(f"[长按] 按住 {key} {duration_ms}ms")

        keyboard = ctx.get_service("keyboard")
        if keyboard:
            keyboard.key_hold(key, duration_ms)
        else:
            ctx.log("[长按] 警告: 键盘服务未注册")

        return NodeResult(success=True)

    def validate(self) -> bool:
        return bool(self.config.get("key")) and self.config.get("duration_ms", 0) > 0

    @classmethod
    def default_config(cls) -> dict:
        return {"key": "", "duration_ms": 500}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "长按",
            "category": "键盘",
            "description": "按住一个键指定时长后释放",
            "config_schema": {
                "key": {"type": "string", "default": "", "description": "按键名称"},
                "duration_ms": {"type": "number", "default": 500, "min": 1, "description": "按住毫秒数"},
            },
        }
