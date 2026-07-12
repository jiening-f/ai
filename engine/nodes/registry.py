"""
节点注册表

管理所有可用的节点类型，提供注册、查询功能。

用法:
    from engine.nodes.registry import NODE_REGISTRY, register_node, get_node_class, list_node_types

验证:
    len(NODE_REGISTRY) == 19
"""

from engine.nodes.base import BaseNode

# 全局节点注册表: node_type → NodeClass
NODE_REGISTRY: dict[str, type[BaseNode]] = {}

# 节点元数据: node_type → {name, category, description, config_schema}
NODE_METADATA: dict[str, dict] = {}


def register_node(cls: type[BaseNode]):
    """
    注册一个节点类

    用法:
        @register_node
        class MyNode(BaseNode):
            node_type = "my_custom"
    """
    if not cls.node_type:
        raise ValueError(f"节点类 {cls.__name__} 必须定义 node_type 类属性")
    NODE_REGISTRY[cls.node_type] = cls
    # 缓存元数据
    try:
        NODE_METADATA[cls.node_type] = cls.description()
    except Exception:
        NODE_METADATA[cls.node_type] = {
            "type": cls.node_type,
            "name": cls.__name__,
            "category": "other",
            "description": "",
            "config_schema": {},
        }
    return cls


def get_node_class(node_type: str) -> type[BaseNode] | None:
    """
    根据节点类型字符串获取对应的节点类

    Args:
        node_type: 节点类型标识，如 "key_press"、"condition"

    Returns:
        节点类，未注册则返回 None
    """
    return NODE_REGISTRY.get(node_type)


def list_node_types() -> list[dict]:
    """
    列出所有已注册的节点类型信息

    Returns:
        节点元数据列表，按分类排序
    """
    result = list(NODE_METADATA.values())
    # 按分类排序
    category_order = {"流程控制": 0, "键盘": 1, "鼠标": 2, "视觉": 3, "数据": 4}
    result.sort(key=lambda x: category_order.get(x.get("category", ""), 99))
    return result


# ── 自动注册所有内置节点 ──────────────────────────

# 流量控制节点
from engine.nodes.flow import StartNode, EndNode, WaitNode, ConditionNode, LoopNode  # noqa: E402
register_node(StartNode)
register_node(EndNode)
register_node(WaitNode)
register_node(ConditionNode)
register_node(LoopNode)
from engine.nodes.subflow import SubFlowNode  # noqa: E402
register_node(SubFlowNode)

# 键盘节点
from engine.nodes.keyboard import KeyPressNode, KeyComboNode, KeyHoldNode  # noqa: E402, F811
register_node(KeyPressNode)
register_node(KeyComboNode)
register_node(KeyHoldNode)

# 鼠标节点
from engine.nodes.mouse import MouseClickNode, MouseDblClickNode, MouseRightNode, MouseDragNode, MouseScrollNode  # noqa: E402
register_node(MouseClickNode)
register_node(MouseDblClickNode)
register_node(MouseRightNode)
register_node(MouseDragNode)
register_node(MouseScrollNode)

# 视觉节点
from engine.nodes.vision import OcrRecognizeNode, TemplateMatchNode, ScreenshotNode  # noqa: E402
register_node(OcrRecognizeNode)
register_node(TemplateMatchNode)
register_node(ScreenshotNode)

# 数据节点
from engine.nodes.data import VariableSetNode, TextOutputNode  # noqa: E402
register_node(VariableSetNode)
register_node(TextOutputNode)
