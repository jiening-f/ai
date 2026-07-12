"""
视觉识别节点

- OcrRecognizeNode: OCR 文字识别
- TemplateMatchNode: 图片模板匹配
- ScreenshotNode: 截图
"""

from engine.nodes.base import BaseNode, NodeResult
from engine.executor.context import ExecutionContext


class OcrRecognizeNode(BaseNode):
    """OCR 文字识别节点"""

    node_type = "ocr_recognize"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        region = self.config.get("region")  # {"x", "y", "w", "h"} 或 None
        lang = self.config.get("lang", "zh-cn")
        target_text = self.config.get("target_text", "")

        ctx.log(f"[OCR] 识别区域: {region or '全屏'}, 语言: {lang}")

        # 获取截图（优先使用上下文缓存的截图）
        screenshot = ctx.screenshot
        if screenshot is None:
            screenshot_service = ctx.get_service("screenshot")
            if screenshot_service:
                screenshot = screenshot_service.capture_fullscreen()
                ctx.screenshot = screenshot
            else:
                return NodeResult(success=False, error_message="截图服务未注册")

        # 调用 OCR 服务
        ocr = ctx.get_service("ocr")
        if ocr:
            results = ocr.recognize(screenshot, region=region, lang=lang)
        else:
            ctx.log("[OCR] 警告: OCR 服务未注册，返回空结果")
            results = []

        # 将结果写入变量
        ctx.set_var("ocr_results", results)
        texts = [r.get("text", "") for r in results]
        ctx.set_var("ocr_texts", texts)
        ctx.set_var("ocr_combined", "".join(texts))

        # 查找目标文字
        found = False
        if target_text:
            for r in results:
                if target_text in r.get("text", ""):
                    found = True
                    ctx.set_var("target_position", r.get("position"))
                    ctx.set_var("target_confidence", r.get("confidence", 0))
                    ctx.log(f"[OCR] 找到目标文字 '{target_text}' 在 {r.get('position')}")
                    break
            if not found:
                ctx.log(f"[OCR] 未找到目标文字 '{target_text}'")
        ctx.set_var("target_found", found)

        return NodeResult(success=True, data={"results": results, "found": found})

    @classmethod
    def default_config(cls) -> dict:
        return {"region": None, "lang": "zh-cn", "target_text": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "OCR 识别",
            "category": "视觉",
            "description": "对截图进行 OCR 文字识别，可搜索指定文字位置",
            "config_schema": {
                "region": {"type": "object", "default": None, "description": "识别区域 {x,y,w,h}，null=全屏"},
                "lang": {"type": "string", "default": "zh-cn", "description": "识别语言"},
                "target_text": {"type": "string", "default": "", "description": "要查找的目标文字，为空则识别全部"},
            },
        }


class TemplateMatchNode(BaseNode):
    """图片模板匹配节点"""

    node_type = "template_match"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        template_path = self.config.get("template_path", "")
        threshold = self.config.get("threshold", 0.8)
        multi = self.config.get("multi", False)
        region = self.config.get("region")

        if not template_path:
            return NodeResult(success=False, error_message="未指定模板图片路径")

        ctx.log(f"[匹配] 模板: {template_path}, 阈值: {threshold}")

        screenshot = ctx.screenshot
        if screenshot is None:
            screenshot_service = ctx.get_service("screenshot")
            if screenshot_service:
                screenshot = screenshot_service.capture_fullscreen()
                ctx.screenshot = screenshot

        if screenshot is None:
            return NodeResult(success=False, error_message="无法获取截图")

        matcher = ctx.get_service("template_matcher")
        if matcher:
            matches = matcher.match(screenshot, template_path, threshold=threshold, multi=multi, region=region)
        else:
            ctx.log("[匹配] 警告: 模板匹配服务未注册")
            matches = []

        ctx.set_var("match_results", matches)
        ctx.set_var("match_found", len(matches) > 0)
        if matches:
            best = matches[0]
            ctx.set_var("match_position", best.get("position"))
            ctx.set_var("match_confidence", best.get("confidence", 0))
            ctx.log(f"[匹配] 找到 {len(matches)} 个匹配，最佳置信度: {best.get('confidence', 0):.3f}")

        return NodeResult(success=True, data={"matches": matches, "found": len(matches) > 0})

    @classmethod
    def default_config(cls) -> dict:
        return {"template_path": "", "threshold": 0.8, "multi": False, "region": None}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "模板匹配",
            "category": "视觉",
            "description": "在截图中查找指定模板图片的位置",
            "config_schema": {
                "template_path": {"type": "string", "default": "", "description": "模板图片文件路径"},
                "threshold": {"type": "number", "default": 0.8, "min": 0, "max": 1, "description": "匹配阈值"},
                "multi": {"type": "boolean", "default": False, "description": "是否多目标匹配"},
                "region": {"type": "object", "default": None, "description": "搜索区域"},
            },
        }


class ScreenshotNode(BaseNode):
    """截图节点"""

    node_type = "screenshot"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        mode = self.config.get("mode", "fullscreen")  # fullscreen / region / window
        region = self.config.get("region")  # {"x", "y", "w", "h"}
        save_path = self.config.get("save_path", "")

        ctx.log(f"[截图] 模式: {mode}")

        screenshot_service = ctx.get_service("screenshot")
        if not screenshot_service:
            return NodeResult(success=False, error_message="截图服务未注册")

        if mode == "fullscreen":
            screenshot = screenshot_service.capture_fullscreen()
        elif mode == "region" and region:
            screenshot = screenshot_service.capture_region(
                region["x"], region["y"], region["w"], region["h"]
            )
        elif mode == "window":
            window = ctx.get_service("window")
            if window and window.current_hwnd:
                screenshot = screenshot_service.capture_window(window.current_hwnd)
            else:
                screenshot = screenshot_service.capture_fullscreen()
        else:
            return NodeResult(success=False, error_message=f"未知截图模式: {mode}")

        # 缓存截图到上下文
        ctx.screenshot = screenshot

        # 保存截图（可选）
        if save_path and screenshot is not None:
            import cv2
            cv2.imwrite(save_path, screenshot)
            ctx.log(f"[截图] 已保存到: {save_path}")

        return NodeResult(success=True)

    @classmethod
    def default_config(cls) -> dict:
        return {"mode": "fullscreen", "region": None, "save_path": ""}

    @classmethod
    def description(cls) -> dict:
        return {
            "type": cls.node_type,
            "name": "截图",
            "category": "视觉",
            "description": "截取屏幕、区域或窗口的画面",
            "config_schema": {
                "mode": {"type": "string", "enum": ["fullscreen", "region", "window"], "default": "fullscreen"},
                "region": {"type": "object", "default": None, "description": "截图区域 {x,y,w,h}"},
                "save_path": {"type": "string", "default": "", "description": "保存路径，空=不保存"},
            },
        }
