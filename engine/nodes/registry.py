"""节点注册表 —— 管理所有节点类型的注册和查询。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode

if TYPE_CHECKING:
    pass

# 全局节点注册表：node_type → 节点类
NODE_REGISTRY: dict[str, type[BaseNode]] = {}


def register_node(node_cls: type[BaseNode]) -> type[BaseNode]:
    """将节点类注册到 NODE_REGISTRY。用作装饰器。

    用法：
        @register_node
        class MyNode(BaseNode):
            node_type = "my_node"
            ...
    """
    if not node_cls.node_type:
        raise ValueError(f"节点类 {node_cls.__name__} 必须定义 node_type 类属性")
    if node_cls.node_type in NODE_REGISTRY:
        raise ValueError(f"节点类型 '{node_cls.node_type}' 已被 {NODE_REGISTRY[node_cls.node_type].__name__} 注册")
    NODE_REGISTRY[node_cls.node_type] = node_cls
    return node_cls


def get_node_class(node_type: str) -> type[BaseNode]:
    """根据类型名获取节点类。

    Raises:
        KeyError: 类型未注册时抛出。
    """
    if node_type not in NODE_REGISTRY:
        raise KeyError(f"未注册的节点类型: '{node_type}'，可用类型: {list(NODE_REGISTRY.keys())}")
    return NODE_REGISTRY[node_type]


def list_node_types() -> list[dict[str, str]]:
    """列出所有已注册节点类型的元数据。

    Returns:
        [{type, category, description}, ...]
    """
    return [
        {
            "type": node_cls.node_type,
            "category": node_cls.node_category,
            "description": node_cls.node_description,
        }
        for node_cls in NODE_REGISTRY.values()
    ]


# ── 导入所有节点类以触发注册 ──
# 必须在导入 registry 后执行，确保 NODE_REGISTRY 被填充

from engine.nodes.flow import (   # noqa: E402
    ConditionNode,
    EndNode,
    LoopNode,
    StartNode,
    WaitNode,
)
from engine.nodes.keyboard import (  # noqa: E402
    KeyComboNode,
    KeyHoldNode,
    KeyPressNode,
)
from engine.nodes.mouse import (    # noqa: E402
    MouseClickNode,
    MouseDblClickNode,
    MouseDragNode,
    MouseMoveNode,
    MouseRightClickNode,
    MouseScrollNode,
)
from engine.nodes.vision import (   # noqa: E402
    OcrRecognizeNode,
    ScreenshotNode,
    TemplateMatchNode,
)
from engine.nodes.data import (     # noqa: E402
    TextOutputNode,
    VariableSetNode,
)

# 批量注册
for _cls in [
    # 流程控制 (5)
    StartNode, EndNode, WaitNode, ConditionNode, LoopNode,
    # 键盘 (3)
    KeyPressNode, KeyComboNode, KeyHoldNode,
    # 鼠标 (6)
    MouseMoveNode, MouseClickNode, MouseDblClickNode, MouseRightClickNode, MouseDragNode, MouseScrollNode,
    # 视觉 (3)
    OcrRecognizeNode, TemplateMatchNode, ScreenshotNode,
    # 数据 (2)
    VariableSetNode, TextOutputNode,
]:
    register_node(_cls)
