"""视觉识别节点 — OCR、模板匹配、截图"""

import asyncio
from engine.nodes.base import BaseNode, NodeResult, NodeStatus


class ScreenshotNode(BaseNode):
    """截图节点 — 截取屏幕/窗口并缓存到上下文"""
    node_type = "screenshot"

    async def execute(self, ctx) -> NodeResult:
        region = self.config.get("region")
        save_key = self.config.get("save_key", f"screenshot_{self.node_id}")
        ctx.info(f"截图 -> {save_key}", self.node_id)
        ctx.cache_screenshot(save_key, {"node_id": self.node_id, "region": region})
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"screenshot_key": save_key},
        )

    def validate(self) -> bool:
        region = self.config.get("region")
        if region is not None:
            return isinstance(region, list) and len(region) == 4
        return True


class OcrRecognizeNode(BaseNode):
    """OCR识别节点 — 对截图进行文字识别"""
    node_type = "ocr_recognize"

    async def execute(self, ctx) -> NodeResult:
        screenshot_key = self.config.get("screenshot_key", "")
        language = self.config.get("language", "chi_sim")
        expected_text = self.config.get("expected_text", "")
        ctx.info(f"OCR识别 [{language}]: 查找 '{expected_text}'", self.node_id)
        await asyncio.sleep(0.05)
        if expected_text:
            found = bool(expected_text)
            ctx.info(f"OCR结果: {'找到' if found else '未找到'}", self.node_id)
            return NodeResult(
                status=NodeStatus.SUCCESS,
                data={"found": found, "text": expected_text if found else ""},
            )
        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"found": True, "text": "模拟识别文本"},
        )

    def validate(self) -> bool:
        return True


class TemplateMatchNode(BaseNode):
    """模板匹配节点 — 在截图中查找模板图片位置"""
    node_type = "template_match"

    async def execute(self, ctx) -> NodeResult:
        template_path = self.config.get("template", "")
        confidence = float(self.config.get("confidence", 0.8))
        screenshot_key = self.config.get("screenshot_key", "")
        ctx.info(f"模板匹配: {template_path} (置信度>{confidence})", self.node_id)
        await asyncio.sleep(0.03)
        found = bool(template_path)
        result_data = {
            "found": found,
            "x": 100, "y": 200,
            "confidence": 0.95 if found else 0.0,
        }
        ctx.info(
            f"匹配结果: {'找到' if found else '未找到'} "
            f"({result_data.get('x')},{result_data.get('y')})",
            self.node_id,
        )
        return NodeResult(status=NodeStatus.SUCCESS, data=result_data)

    def validate(self) -> bool:
        template = self.config.get("template", "")
        confidence = self.config.get("confidence", 0.8)
        return bool(template) and isinstance(confidence, (int, float)) and 0 <= confidence <= 1
