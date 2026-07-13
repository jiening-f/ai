"""节点注册表 — 类型注册、查询、元数据管理"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.nodes.base import BaseNode

# ── 全局注册表 ──
NODE_REGISTRY: dict[str, type[BaseNode]] = {}
"""节点类型 → 节点类的映射"""

NODE_METADATA: dict[str, dict] = {}
"""节点类型 → {category, name, description} 的元数据映射"""


def register_node(node_type: str, category: str, name: str, description: str):
    """节点注册装饰器

    用法:
        @register_node("key_press", "键盘", "按键", "按下指定按键")
        class KeyPressNode(BaseNode):
            ...

    Args:
        node_type: 节点类型字符串（唯一标识，如 "key_press"）
        category: 分类（流程控制 / 键盘 / 鼠标 / 视觉 / 数据）
        name: 中文名称
        description: 功能说明
    """
    def decorator(cls: type[BaseNode]) -> type[BaseNode]:
        cls.node_type = node_type  # 注入类型标识
        NODE_REGISTRY[node_type] = cls
        NODE_METADATA[node_type] = {
            "category": category,
            "name": name,
            "description": description,
        }
        return cls
    return decorator


def get_node_class(node_type: str) -> type[BaseNode] | None:
    """根据类型字符串获取节点类

    Args:
        node_type: 节点类型字符串（如 "key_press"）

    Returns:
        节点类，未注册则返回 None
    """
    return NODE_REGISTRY.get(node_type)


def list_node_types(category: str | None = None) -> list[dict]:
    """列出所有已注册的节点类型（含名称、分类、描述）

    Args:
        category: 可选，按分类过滤

    Returns:
        节点类型信息列表，按分类分组排列
    """
    result = []
    for node_type, meta in NODE_METADATA.items():
        if category and meta["category"] != category:
            continue
        result.append({
            "type": node_type,
            "name": meta["name"],
            "category": meta["category"],
            "description": meta["description"],
        })
    # 按分类排序
    category_order = {"流程控制": 0, "键盘": 1, "鼠标": 2, "视觉": 3, "数据": 4}
    result.sort(key=lambda x: (category_order.get(x["category"], 99), x["type"]))
    return result
