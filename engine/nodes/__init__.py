"""节点系统 — 20 种节点类型导出"""

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

from engine.nodes.flow import (
    StartNode, EndNode, WaitNode, LogNode, ConditionNode, LoopNode,
)

from engine.nodes.input import (
    KeyPressNode, KeyComboNode, KeyHoldNode,
    MouseMoveNode, MouseClickNode, MouseDblClickNode,
    MouseRightNode, MouseDragNode, MouseScrollNode,
)

from engine.nodes.vision import (
    ScreenshotNode, OcrRecognizeNode, TemplateMatchNode,
)

from engine.nodes.variable import (
    VariableSetNode, TextOutputNode,
)

# 节点类型注册表
NODE_REGISTRY: dict[str, type] = {
    "start": StartNode, "end": EndNode,
    "wait": WaitNode, "log": LogNode,
    "condition": ConditionNode, "loop": LoopNode,
    "key_press": KeyPressNode, "key_combo": KeyComboNode,
    "key_hold": KeyHoldNode, "mouse_move": MouseMoveNode,
    "mouse_click": MouseClickNode, "mouse_dblclick": MouseDblClickNode,
    "mouse_right": MouseRightNode, "mouse_drag": MouseDragNode,
    "mouse_scroll": MouseScrollNode,
    "ocr_recognize": OcrRecognizeNode, "template_match": TemplateMatchNode,
    "screenshot": ScreenshotNode,
    "variable_set": VariableSetNode, "text_output": TextOutputNode,
}


def create_node(node_type: str, node_id: str, config: dict = None) -> BaseNode:
    """根据类型字符串创建节点实例"""
    cls = NODE_REGISTRY.get(node_type)
    if cls is None:
        raise ValueError(f"未知节点类型: {node_type}")
    return cls(node_id, config or {})
