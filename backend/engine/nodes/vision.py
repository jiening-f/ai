"""视觉节点 — ocr_recognize, template_match, screenshot"""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.registry import register_node

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


@register_node("ocr_recognize", "视觉", "OCR 文字识别", "在屏幕上识别指定文字并返回坐标")
class OcrRecognizeNode(BaseNode):
    """OCR 文字识别节点 — 检测屏幕中是否包含目标文字

    Config:
        target_text: 要识别的目标文字（支持 | 分隔多个备选）
        region: 可选，截图区域 [x, y, w, h]
        timeout: 超时时间，单位秒（默认 5.0）
        min_confidence: 最小置信度（默认 0.3）
    """
    default_config = {
        "target_text": ...,
        "region": None,
        "timeout": 5.0,
        "min_confidence": 0.3,
    }

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        target = str(self.config.get("target_text", ""))
        region = self.config.get("region")
        timeout = float(self.config.get("timeout", 5.0))
        min_conf = float(self.config.get("min_confidence", 0.3))

        if not target:
            return NodeResult.fail("未指定 OCR 目标文字")

        ctx.log(f"👁 OCR 识别: «{target}»")
        try:
            from engine.vision import OCR
            pos = OCR.find_text(target, region=region, timeout=timeout, min_conf=min_conf)
            if pos:
                ctx.log(f"👁 OCR 命中: «{target}» → ({pos[0]}, {pos[1]})")
                return NodeResult.ok(x=pos[0], y=pos[1], text=target)
            else:
                ctx.log(f"👁 OCR 未找到: «{target}»")
                return NodeResult.fail(f"未找到文字 «{target}»")
        except Exception as e:
            return NodeResult.fail(f"OCR 异常: {e}")

    def validate(self) -> bool:
        target = self.config.get("target_text")
        return target is not None and str(target).strip() != ""


@register_node("template_match", "视觉", "模板匹配", "在屏幕上查找指定模板图片的位置")
class TemplateMatchNode(BaseNode):
    """模板匹配节点 — 在屏幕截图中查找模板图片

    Config:
        template_name: 模板图片名称（不含扩展名）
        region: 可选，搜索区域 [x, y, w, h]
        threshold: 匹配阈值（默认 0.72）
    """
    default_config = {
        "template_name": ...,
        "region": None,
        "threshold": 0.72,
    }

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        template_name = str(self.config.get("template_name", ""))
        region = self.config.get("region")
        threshold = float(self.config.get("threshold", 0.72))

        if not template_name:
            return NodeResult.fail("未指定模板图片名称")

        ctx.log(f"👁 模板匹配: «{template_name}»")
        try:
            from engine.vision import TemplateMatcher
            pos = TemplateMatcher.find(template_name, region=region, conf=threshold)
            if pos:
                ctx.log(f"👁 模板命中: «{template_name}» → ({pos[0]}, {pos[1]})")
                return NodeResult.ok(x=pos[0], y=pos[1], template=template_name)
            else:
                ctx.log(f"👁 模板未匹配: «{template_name}»")
                return NodeResult.fail(f"未匹配模板 «{template_name}»")
        except Exception as e:
            return NodeResult.fail(f"模板匹配异常: {e}")

    def validate(self) -> bool:
        template = self.config.get("template_name")
        threshold = self.config.get("threshold", 0)
        return template is not None and str(template).strip() != "" and 0 <= threshold <= 1


@register_node("screenshot", "视觉", "截图", "截取指定区域的屏幕图像")
class ScreenshotNode(BaseNode):
    """截图节点 — 截取屏幕区域并缓存到上下文

    Config:
        region: 可选，截图区域 [x, y, w, h]（None 表示全屏）
        save_to_var: 可选，将截图路径保存到变量名
    """
    default_config = {"region": None, "save_to_var": None}

    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        region = self.config.get("region")
        save_to_var = self.config.get("save_to_var")

        ctx.log("📸 截图" + (f" region={region}" if region else "（全屏）"))
        try:
            from engine.vision import Screenshot
            img = Screenshot.capture(region=region)
            if img is not None:
                ctx.cache_screenshot(img)
                h, w = img.shape[:2]
                ctx.log(f"📸 截图成功: {w}×{h}")
                result = NodeResult.ok(width=w, height=h)
                if save_to_var:
                    ctx.set_var(save_to_var, f"{w}x{h}")
                return result
            else:
                return NodeResult.fail("截图失败：返回空图像")
        except Exception as e:
            return NodeResult.fail(f"截图异常: {e}")

    def validate(self) -> bool:
        region = self.config.get("region")
        if region is not None:
            if not isinstance(region, (list, tuple)) or len(region) != 4:
                return False
        return True
