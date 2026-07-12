"""视觉识别节点：ocr_recognize, template_match, screenshot。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.nodes.base import BaseNode, NodeResult, NodeStatus

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class OcrRecognizeNode(BaseNode):
    """OCR 文字识别节点。"""
    node_type = "ocr_recognize"
    node_category = "视觉"
    node_description = "对指定区域进行 OCR 文字识别"
    default_config = {
        "region": None,          # [x, y, w, h] 或 None（全屏）
        "language": "ch",        # 识别语言
        "expected_text": None,   # 期望匹配的文字（可选）
        "save_to_var": None,     # 结果存入变量名
    }

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        region = self.config.get("region")
        language = self.config.get("language", "ch")
        expected = self.config.get("expected_text")
        save_to = self.config.get("save_to_var")

        region_str = f"区域 {region}" if region else "全屏"
        ctx.log(f"[ocr_recognize] OCR 识别 {region_str} (语言: {language})")

        # 实际 OCR 由 vision 子系统执行，此处为节点定义层
        recognized_text = ""  # 占位：实际由 vision 子系统填充
        matched = expected is None or (expected in recognized_text if recognized_text else False)

        if save_to:
            ctx.set_var(save_to, recognized_text)

        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={
                "text": recognized_text,
                "matched": matched,
                "region": region,
            },
        )

    def validate(self) -> bool:
        language = self.config.get("language", "")
        return isinstance(language, str) and len(language) > 0


class TemplateMatchNode(BaseNode):
    """图片模板匹配节点。"""
    node_type = "template_match"
    node_category = "视觉"
    node_description = "在屏幕截图中匹配指定模板图片"
    default_config = {
        "template_path": "",         # 模板图片路径
        "threshold": 0.8,            # 匹配阈值 (0.0 ~ 1.0)
        "region": None,              # 搜索区域 [x, y, w, h] 或 None
        "save_position_to": None,    # 匹配到的坐标存入变量
    }

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        template = self.config.get("template_path", "")
        threshold = self.config.get("threshold", 0.8)

        ctx.log(f"[template_match] 匹配模板 {template} (阈值: {threshold})")

        # 实际匹配由 vision 子系统执行
        found = False
        position = None

        save_to = self.config.get("save_position_to")
        if save_to and position:
            ctx.set_var(save_to, position)

        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"found": found, "position": position, "template": template},
        )

    def validate(self) -> bool:
        template = self.config.get("template_path", "")
        threshold = self.config.get("threshold", 0.8)
        return isinstance(template, str) and len(template) > 0 and 0 <= threshold <= 1


class ScreenshotNode(BaseNode):
    """截图节点。"""
    node_type = "screenshot"
    node_category = "视觉"
    node_description = "截取屏幕或窗口指定区域并缓存"
    default_config = {
        "region": None,             # [x, y, w, h] 或 None（全屏/窗口）
        "save_to_var": "screenshot",  # 截图存入上下文变量
        "save_to_file": None,       # 截图保存路径（可选）
    }

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        region = self.config.get("region")
        save_to_var = self.config.get("save_to_var", "screenshot")
        save_to_file = self.config.get("save_to_file")

        region_str = f"区域 {region}" if region else "全屏/窗口"
        ctx.log(f"[screenshot] 截图 {region_str}")

        # 实际截图由 vision 子系统执行，结果缓存到上下文
        ctx.screenshot_cache = None  # 占位：实际由 vision 子系统填充

        return NodeResult(
            status=NodeStatus.SUCCESS,
            data={"region": region, "saved_to": save_to_file},
        )
