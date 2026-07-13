"""节点模块 — 所有节点类型和注册表"""
from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import NODE_REGISTRY, register_node, get_node_class, list_node_types

# 导入所有节点模块以触发注册
from engine.nodes import flow      # noqa: F401
from engine.nodes import keyboard  # noqa: F401
from engine.nodes import mouse     # noqa: F401
from engine.nodes import vision    # noqa: F401
from engine.nodes import data      # noqa: F401

__all__ = [
    "BaseNode", "NodeResult",
    "NODE_REGISTRY", "register_node", "get_node_class", "list_node_types",
]
