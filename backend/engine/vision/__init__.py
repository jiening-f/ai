"""视觉子系统 — 截图 / OCR / 模板匹配

模块结构:
    screenshot.py  — Screenshot 截图服务（GDI / PrintWindow / mss）
    ocr.py         — OCR 文字识别（Windows OCR / EasyOCR）
    template.py    — TemplateMatcher 模板匹配（多尺度 + 颜色验证）

向后兼容:
    所有旧接口别名均保留，现有代码无需修改。
"""

from engine.vision.screenshot import Screenshot
from engine.vision.ocr import OCR, OCRResult
from engine.vision.template import (
    TemplateMatcher,
    MatchResult,
    MATCH_METHODS,
    set_fast_mode,
)

# ── 公共 API ──
__all__ = [
    # 截图
    "Screenshot",
    # OCR
    "OCR",
    "OCRResult",
    # 模板匹配
    "TemplateMatcher",
    "MatchResult",
    "MATCH_METHODS",
    "set_fast_mode",
    # 向后兼容别名
    "tmpl_find",
    "ocr_find",
    "_shot",
    "_shot_bg",
    "_init_ocr",
    "_init_ocr_windows",
    "_ocr_scan",
]

# ── 向后兼容别名 ──
# 这些别名供旧代码使用，保持接口不变
tmpl_find = TemplateMatcher.find
ocr_find = OCR.find_text
_shot = Screenshot.capture
_shot_bg = Screenshot.capture_window
_init_ocr = OCR.instance().init
_init_ocr_windows = OCR.instance()._create_windows_ocr
_ocr_scan = OCR.instance().scan
