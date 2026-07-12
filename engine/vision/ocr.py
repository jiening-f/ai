"""
OCR 文字识别服务

自动选择可用引擎：
1. Windows OCR（系统内置，无需安装）— 首选
2. EasyOCR（pip install easyocr）— 降级方案
"""

import numpy as np


class OcrService:
    """
    OCR 识别服务

    用法:
        ocr = OcrService()
        results = ocr.recognize(img, lang="zh-cn")
        # results: [{"text": "...", "position": (x,y,w,h), "confidence": 0.95}, ...]
    """

    def __init__(self, engine: str = "auto"):
        """
        Args:
            engine: "windows" | "easyocr" | "auto" (自动选择)
        """
        self.engine = engine
        self._ocr_instance = None
        self._initialized = False

    def _init_engine(self):
        """延迟初始化 OCR 引擎"""
        if self._initialized:
            return

        if self.engine == "auto":
            # 优先 Windows OCR
            self._ocr_instance = self._create_windows_ocr()
            if self._ocr_instance is None:
                self._ocr_instance = self._create_easyocr()
        elif self.engine == "windows":
            self._ocr_instance = self._create_windows_ocr()
        elif self.engine == "easyocr":
            self._ocr_instance = self._create_easyocr()

        self._initialized = True

    def _create_windows_ocr(self):
        """尝试创建 Windows OCR 实例"""
        try:
            import winsdk.windows.media.ocr as win_ocr
            import winsdk.windows.graphics.imaging as win_img
            import winsdk.windows.storage.streams as win_streams
            return {"type": "windows"}
        except ImportError:
            return None

    def _create_easyocr(self):
        """尝试创建 EasyOCR 实例"""
        try:
            import easyocr
            return easyocr.Reader(["ch_sim", "en"], gpu=False)
        except ImportError:
            return None

    def recognize(
        self,
        img: np.ndarray,
        region: dict | None = None,
        lang: str = "zh-cn",
    ) -> list[dict]:
        """
        识别图像中的文字

        Args:
            img: 输入图像 numpy array (BGR)
            region: 识别区域 {"x","y","w","h"}，None=全图
            lang: 识别语言 zh-cn / en

        Returns:
            [{"text": "...", "position": (x,y,w,h), "confidence": 0.95}, ...]
        """
        self._init_engine()

        if self._ocr_instance is None:
            return []

        # 区域截取
        roi = img
        offset_x, offset_y = 0, 0
        if region and isinstance(region, dict):
            rx, ry, rw, rh = region.get("x", 0), region.get("y", 0), region.get("w", 0), region.get("h", 0)
            if rw > 0 and rh > 0:
                roi = img[ry:ry + rh, rx:rx + rw]
                offset_x, offset_y = rx, ry

        if self._ocr_instance.get("type") == "windows":
            return self._recognize_windows(roi, lang, offset_x, offset_y)
        else:
            return self._recognize_easyocr(roi, offset_x, offset_y)

    # ── Windows OCR 实现 ──────────────────

    async def recognize_async(
        self,
        img: np.ndarray,
        region: dict | None = None,
        lang: str = "zh-cn",
    ) -> list[dict]:
        """异步版识别（Windows OCR 需要异步）"""
        self._init_engine()

        roi = img
        offset_x, offset_y = 0, 0
        if region and isinstance(region, dict):
            rx, ry, rw, rh = region.get("x", 0), region.get("y", 0), region.get("w", 0), region.get("h", 0)
            if rw > 0 and rh > 0:
                roi = img[ry:ry + rh, rx:rx + rw]
                offset_x, offset_y = rx, ry

        if self._ocr_instance and self._ocr_instance.get("type") == "windows":
            return await self._recognize_windows_async(roi, lang, offset_x, offset_y)
        else:
            return self.recognize(img, region, lang)

    async def _recognize_windows_async(self, img: np.ndarray, lang: str, offset_x: int, offset_y: int) -> list[dict]:
        """Windows OCR 异步实现"""
        import winsdk.windows.media.ocr as win_ocr
        import winsdk.windows.graphics.imaging as win_img
        import winsdk.windows.storage.streams as win_streams

        import cv2
        import asyncio

        # BGR → RGBA
        if len(img.shape) == 3:
            rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        else:
            rgba = cv2.cvtColor(img, cv2.COLOR_GRAY2RGBA)

        # NumPy → SoftwareBitmap
        h, w = rgba.shape[:2]
        stream = win_streams.InMemoryRandomAccessStream()
        encoder = await win_img.BitmapEncoder.create_async(win_img.BitmapEncoder.png_encoder_id, stream)
        encoder.set_software_bitmap(
            win_img.SoftwareBitmap.create_copy_from_buffer(
                rgba.tobytes(),
                win_img.BitmapPixelFormat.rgba8,
                w, h,
                win_img.BitmapAlphaMode.premultiplied,
            )
        )
        await encoder.flush_async()

        # 解码
        decoder = await win_img.BitmapDecoder.create_async(stream)
        software_bitmap = await decoder.get_software_bitmap_async()
        software_bitmap = await win_img.SoftwareBitmap.convert(
            software_bitmap, win_img.BitmapPixelFormat.rgba8
        )

        # OCR
        engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            engine = win_ocr.OcrEngine.try_create_from_language(
                win_ocr.OcrEngine.available_recognizer_languages[0]
            )

        ocr_result = await engine.recognize_async(software_bitmap)

        results = []
        for line in ocr_result.lines:
            for word in line.words:
                rect = word.bounding_rect
                results.append({
                    "text": word.text,
                    "position": {
                        "x": rect.x + offset_x, "y": rect.y + offset_y,
                        "w": rect.width, "h": rect.height,
                    },
                    "confidence": 0.95,  # Windows OCR 不返回逐词置信度
                })

        return results

    def _recognize_windows(self, img: np.ndarray, lang: str, offset_x: int, offset_y: int) -> list[dict]:
        """Windows OCR 同步封装（有限支持）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 运行中无法嵌套，降级到 EasyOCR
                return self._recognize_easyocr(img, offset_x, offset_y)
            return loop.run_until_complete(
                self._recognize_windows_async(img, lang, offset_x, offset_y)
            )
        except RuntimeError:
            return asyncio.run(
                self._recognize_windows_async(img, lang, offset_x, offset_y)
            )

    # ── EasyOCR 实现 ──────────────────

    def _recognize_easyocr(self, img: np.ndarray, offset_x: int, offset_y: int) -> list[dict]:
        """EasyOCR 识别"""
        if self._ocr_instance is None:
            return []

        raw = self._ocr_instance.readtext(img)

        results = []
        for bbox, text, confidence in raw:
            x1, y1 = int(bbox[0][0]), int(bbox[0][1])
            x2, y2 = int(bbox[2][0]), int(bbox[2][1])
            results.append({
                "text": text,
                "position": {
                    "x": x1 + offset_x,
                    "y": y1 + offset_y,
                    "w": x2 - x1,
                    "h": y2 - y1,
                },
                "confidence": round(float(confidence), 4),
            })

        return results
