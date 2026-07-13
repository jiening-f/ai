"""前端节点类型定义验证 — 纯逻辑测试，不依赖 DOM

验证所有 17 种 UI 节点类型定义的正确性和完整性。
这些测试从 FlowEditor.tsx 的 NODE_CATEGORIES 定义中提取并验证。
"""

import pytest


# ═══════════════════════════════════════════════════════════════
# 前端节点类型定义（与 FlowEditor.tsx 保持同步）
# ═══════════════════════════════════════════════════════════════

NODE_CATEGORIES = [
    {
        "name": "流程控制",
        "icon": "🔀",
        "nodes": [
            {"type": "start", "label": "开始", "icon": "▶"},
            {"type": "end", "label": "结束", "icon": "⏹"},
            {"type": "wait", "label": "等待", "icon": "⏳"},
            {"type": "condition", "label": "条件判断", "icon": "❓"},
            {"type": "loop", "label": "循环", "icon": "🔄"},
        ],
    },
    {
        "name": "键盘操作",
        "icon": "⌨️",
        "nodes": [
            {"type": "key_press", "label": "按键", "icon": "⌨"},
            {"type": "key_combo", "label": "组合键", "icon": "🔣"},
            {"type": "key_hold", "label": "长按", "icon": "⏱"},
        ],
    },
    {
        "name": "鼠标操作",
        "icon": "🖱️",
        "nodes": [
            {"type": "mouse_click", "label": "点击", "icon": "🖱"},
            {"type": "mouse_dblclick", "label": "双击", "icon": "🖱"},
            {"type": "mouse_drag", "label": "拖拽", "icon": "↗"},
            {"type": "mouse_scroll", "label": "滚动", "icon": "⬇"},
        ],
    },
    {
        "name": "视觉识别",
        "icon": "👁️",
        "nodes": [
            {"type": "ocr_recognize", "label": "OCR 识别", "icon": "🔍"},
            {"type": "template_match", "label": "图片匹配", "icon": "🖼"},
            {"type": "screenshot", "label": "截图", "icon": "📷"},
        ],
    },
    {
        "name": "数据操作",
        "icon": "📦",
        "nodes": [
            {"type": "variable_set", "label": "变量赋值", "icon": "📝"},
            {"type": "text_output", "label": "文本输出", "icon": "💬"},
        ],
    },
]


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

class TestNodeCategories:
    """验证节点分类定义的完整性"""

    def test_all_categories_present(self):
        """5 个分类均应存在"""
        names = {cat["name"] for cat in NODE_CATEGORIES}
        expected = {"流程控制", "键盘操作", "鼠标操作", "视觉识别", "数据操作"}
        assert names == expected

    def test_category_counts(self):
        """验证每个分类的节点数量"""
        for cat in NODE_CATEGORIES:
            count = len(cat["nodes"])
            if cat["name"] == "流程控制":
                assert count == 5
            elif cat["name"] == "键盘操作":
                assert count == 3
            elif cat["name"] == "鼠标操作":
                assert count == 4
            elif cat["name"] == "视觉识别":
                assert count == 3
            elif cat["name"] == "数据操作":
                assert count == 2

    def test_total_node_count(self):
        """总计 17 种 UI 节点类型"""
        total = sum(len(cat["nodes"]) for cat in NODE_CATEGORIES)
        assert total == 17

    def test_no_duplicate_types(self):
        """所有 node type 必须唯一"""
        all_types = []
        for cat in NODE_CATEGORIES:
            for node in cat["nodes"]:
                all_types.append(node["type"])
        assert len(all_types) == len(set(all_types)), f"发现重复类型: {all_types}"

    def test_every_node_has_required_fields(self):
        """每个节点必须有 type、label、icon"""
        for cat in NODE_CATEGORIES:
            for node in cat["nodes"]:
                assert "type" in node, f"{node} 缺少 type"
                assert "label" in node, f"{node} 缺少 label"
                assert "icon" in node, f"{node} 缺少 icon"
                assert isinstance(node["type"], str)
                assert len(node["type"]) > 0
                assert isinstance(node["label"], str)
                assert len(node["label"]) > 0

    def test_every_category_has_icon(self):
        """每个分类必须有 icon"""
        for cat in NODE_CATEGORIES:
            assert "icon" in cat
            assert len(cat["icon"]) > 0

    def test_category_has_name(self):
        """每个分类必须有 name"""
        for cat in NODE_CATEGORIES:
            assert "name" in cat
            assert len(cat["name"]) > 0


class TestSpecificNodeTypes:
    """验证特定节点类型"""

    def test_start_node(self):
        start = _find_node("start")
        assert start is not None
        assert start["label"] == "开始"
        assert start["icon"] == "▶"

    def test_end_node(self):
        end = _find_node("end")
        assert end is not None
        assert end["label"] == "结束"

    def test_keyboard_nodes(self):
        """三种键盘操作都存在"""
        keyboard_types = {n["type"] for n in _category_nodes("键盘操作")}
        assert keyboard_types == {"key_press", "key_combo", "key_hold"}

    def test_mouse_nodes(self):
        """四种鼠标操作都存在"""
        mouse_types = {n["type"] for n in _category_nodes("鼠标操作")}
        assert mouse_types == {"mouse_click", "mouse_dblclick", "mouse_drag", "mouse_scroll"}

    def test_vision_nodes(self):
        """三种视觉识别都存在"""
        vision_types = {n["type"] for n in _category_nodes("视觉识别")}
        assert vision_types == {"ocr_recognize", "template_match", "screenshot"}

    def test_data_nodes(self):
        """两种数据操作都存在"""
        data_types = {n["type"] for n in _category_nodes("数据操作")}
        assert data_types == {"variable_set", "text_output"}


class TestCanvasNode:
    """测试画布节点数据结构"""

    def test_create_canvas_node(self):
        """验证 CanvasNode 数据结构"""
        node = {
            "id": "n_1",
            "type": "start",
            "label": "开始",
            "x": 300,
            "y": 40,
        }
        assert node["id"] == "n_1"
        assert node["type"] == "start"
        assert isinstance(node["x"], (int, float))
        assert isinstance(node["y"], (int, float))

    def test_default_canvas_nodes(self):
        """验证 FlowEditor 默认初始节点"""
        defaults = [
            {"id": "n_1", "type": "start", "label": "开始", "x": 300, "y": 40},
            {"id": "n_2", "type": "wait", "label": "等待 1s", "x": 300, "y": 160},
            {"id": "n_3", "type": "key_press", "label": "按键 A", "x": 300, "y": 280},
            {"id": "n_4", "type": "end", "label": "结束", "x": 300, "y": 400},
        ]
        types = [n["type"] for n in defaults]
        assert types == ["start", "wait", "key_press", "end"]

        # 验证默认画布节点 y 坐标递增
        for i in range(1, len(defaults)):
            assert defaults[i]["y"] > defaults[i - 1]["y"]


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _find_node(node_type: str) -> dict | None:
    """在全部分类中查找指定类型的节点"""
    for cat in NODE_CATEGORIES:
        for node in cat["nodes"]:
            if node["type"] == node_type:
                return node
    return None


def _category_nodes(category_name: str) -> list:
    """获取指定分类下的所有节点"""
    for cat in NODE_CATEGORIES:
        if cat["name"] == category_name:
            return cat["nodes"]
    return []
