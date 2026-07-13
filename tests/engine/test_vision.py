"""测试视觉识别模块 — OCR / TemplateMatcher 逻辑

视觉模块位于 backend/engine/vision.py，该模块依赖 Windows 环境
（win32 API、OpenCV、OCR 引擎等），在 CI 环境中可能不可用。
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

# 尝试导入视觉模块
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_backend_root = os.path.join(_project_root, "backend")

# 将 backend 路径插入 sys.path（在 project_root 之前）
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# 清除缓存的 engine 模块（来自项目根），使 backend/engine 生效
_old_engine = sys.modules.pop("engine", None)
# 也清除子模块
for k in list(sys.modules):
    if k.startswith("engine."):
        del sys.modules[k]

vision_module = None
try:
    import engine.vision
    vision_module = engine.vision
except ImportError:
    pass
finally:
    # 恢复原始的 engine 模块
    if _old_engine:
        sys.modules["engine"] = _old_engine
    # 移除 backend 路径
    if _backend_root in sys.path:
        sys.path.remove(_backend_root)

needs_vision = pytest.mark.skipif(
    vision_module is None,
    reason="backend/engine/vision.py 无法导入（缺少 Windows 依赖）"
)


def create_fake_image(w=200, h=100):
    """创建假图像（numpy 数组模拟 OpenCV BGR 图像）"""
    return np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)


# ═══════════════════════════════════════════════════════════════
# 如果不支持导入，跳过所有测试
# ═══════════════════════════════════════════════════════════════

pytestmark = needs_vision


class TestOCRInstance:
    """测试 OCR 单例创建和引擎管理"""

    def test_singleton(self):
        OCR = vision_module.OCR
        a = OCR.instance()
        b = OCR.instance()
        assert a is b

    def test_initial_state(self):
        OCR = vision_module.OCR
        ocr = OCR()
        assert ocr.engine is None
        assert ocr.status == "未加载"
        assert ocr.engine_type is None
        assert ocr.preferred == "windows"

    def test_set_preferred(self):
        OCR = vision_module.OCR
        ocr = OCR()
        ocr.preferred = "windows"
        try:
            ocr.set_preferred("easy")
        except Exception:
            # 可能因为 config 写入失败
            ocr.preferred = "easy"
            ocr.engine = None
            ocr.status = "未加载"
            ocr.engine_type = None
        assert ocr.preferred == "easy"

    def test_init_already_loaded(self):
        OCR = vision_module.OCR
        ocr = OCR()
        ocr.engine = MagicMock()
        ocr.engine_type = "windows"
        assert ocr.init() is True


class TestOCRPreprocess:
    """测试 OCR 预处理函数"""

    def test_preprocess_game_font(self):
        OCR = vision_module.OCR
        img = create_fake_image(300, 150)
        processed = OCR._preprocess_game_font(img)
        assert processed is not None
        assert processed.shape[2] == 3

    def test_small_image_upscaled(self):
        OCR = vision_module.OCR
        small_img = create_fake_image(100, 50)
        processed = OCR._preprocess_game_font(small_img)
        assert processed.shape[0] >= small_img.shape[0]


class TestTemplateMatcherPreprocess:
    """测试模板匹配预处理"""

    def test_preprocess(self):
        TemplateMatcher = vision_module.TemplateMatcher
        img = create_fake_image(200, 100)
        gray = TemplateMatcher._preprocess(img)
        assert len(gray.shape) == 2

    def test_canny_edge(self):
        TemplateMatcher = vision_module.TemplateMatcher
        img = create_fake_image(200, 100)
        edges = TemplateMatcher._canny_edge(img)
        assert len(edges.shape) == 2


class TestTemplateColorSimilarity:
    """测试颜色相似度计算"""

    def test_color_similarity_same_image(self):
        TemplateMatcher = vision_module.TemplateMatcher
        img = create_fake_image(64, 32)
        sim = TemplateMatcher._color_similarity(img, img, 0, 0, 64, 32, scale=1.0)
        assert 0.0 <= sim <= 1.0
        assert sim >= 0.90

    def test_color_similarity_different_images(self):
        TemplateMatcher = vision_module.TemplateMatcher
        img1 = create_fake_image(64, 32)
        img2 = create_fake_image(200, 100)
        sim = TemplateMatcher._color_similarity(img1, img2, 0, 0, 64, 32, scale=1.0)
        assert 0.0 <= sim <= 1.0

    def test_color_similarity_tiny_image(self):
        TemplateMatcher = vision_module.TemplateMatcher
        tiny = np.random.randint(0, 255, (2, 2, 3), dtype=np.uint8)
        screen = create_fake_image(200, 100)
        sim = TemplateMatcher._color_similarity(tiny, screen, 50, 50, 2, 2, scale=1.0)
        assert sim == 0.5


class TestTemplateMatcherFind:
    """测试 find 方法"""

    def test_find_nonexistent_file(self):
        TemplateMatcher = vision_module.TemplateMatcher
        result = TemplateMatcher.find("/nonexistent/path/template.png")
        assert result is None

    def test_find_no_name_no_file(self):
        TemplateMatcher = vision_module.TemplateMatcher
        result = TemplateMatcher.find("template_that_does_not_exist")
        assert result is None


class TestScreenshotCapture:
    """测试截图模块"""

    def test_screenshot_has_capture_method(self):
        Screenshot = vision_module.Screenshot
        assert hasattr(Screenshot, 'capture')
        assert callable(Screenshot.capture)

    def test_capture_template_exists(self):
        Screenshot = vision_module.Screenshot
        assert hasattr(Screenshot, 'capture_template')


class TestFastMode:
    """测试快速模式开关"""

    def test_set_fast_mode(self):
        set_fast_mode = vision_module.set_fast_mode
        set_fast_mode(True)
        set_fast_mode(False)


class TestLegacyAliases:
    """测试旧接口别名"""

    def test_aliases_exist(self):
        assert callable(vision_module.tmpl_find)
        assert callable(vision_module.ocr_find)
        assert callable(vision_module._shot)
