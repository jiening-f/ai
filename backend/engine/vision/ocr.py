"""视觉子系统 - OCR 文字识别

支持两种 OCR 引擎：
1. Windows OCR（系统内置，优先）- 通过 winrt 调用
2. EasyOCR（pip 安装，降级）- 离线可用，支持多语言

引擎实例在 init() 时创建并缓存，避免重复初始化。
"""

import threading
import time
from typing import Optional, List, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from core.constants import _flog

# ── 识别结果类型 ──
# 每个结果: (center_x, center_y, text, confidence)
OCRResult = Tuple[int, int, str, float]


class OCR:
    """OCR 文字识别服务（单例）

    用法:
        ocr = OCR.instance()
        ocr.init()                       # 初始化引擎
        results = ocr.scan(img)          # 扫描图像
        pos = OCR.find_text("目标文字")   # 查找特定文字位置
    """

    _inst: Optional["OCR"] = None

    def __init__(self):
        self._engine = None          # 缓存的 OCR 引擎实例
        self._engine_type: Optional[str] = None  # "windows" | "easyocr"
        self._status: str = "未加载"
        self._preferred: str = "windows"
        self._lock = threading.Lock()

    # ── 单例 ──

    @classmethod
    def instance(cls) -> "OCR":
        """获取 OCR 单例"""
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    # ── 属性 ──

    @property
    def engine_type(self) -> Optional[str]:
        return self._engine_type

    @property
    def status(self) -> str:
        return self._status

    # ── 初始化 ──

    def init(self) -> bool:
        """初始化 OCR 引擎（线程安全，已缓存则直接返回）"""
        if self._engine is not None:
            return True

        with self._lock:
            if self._engine is not None:
                return True

            self._status = "加载中..."

            # 按优先级尝试引擎
            engines = [self._preferred]
            if self._preferred == "windows":
                engines.append("easyocr")
            else:
                engines.append("windows")

            for engine_name in engines:
                if engine_name == "windows":
                    if self._try_init_windows():
                        return True
                elif engine_name == "easyocr":
                    if self._try_init_easyocr():
                        return True

            self._status = "OCR 初始化失败"
            return False

    def _try_init_windows(self) -> bool:
        """尝试初始化 Windows OCR 引擎"""
        _flog("OCR: 尝试 Windows OCR...")
        try:
            eng = self._create_windows_ocr()
            if eng is not None:
                self._engine = eng
                self._engine_type = "windows"
                self._status = "Windows OCR 就绪"
                _flog("OCR: Windows OCR 加载成功")
                return True
        except Exception as e:
            _flog(f"OCR: Windows OCR 异常: {e}")

        self._engine = None
        _flog("OCR: Windows OCR 不可用，降级 EasyOCR")
        return False

    def _try_init_easyocr(self) -> bool:
        """尝试初始化 EasyOCR 引擎"""
        _flog("OCR: 尝试 EasyOCR...")
        try:
            eng = self._create_easyocr()
            if eng is not None:
                self._engine = eng
                self._engine_type = "easyocr"
                self._status = "EasyOCR 就绪"
                _flog("OCR: EasyOCR 加载成功")
                return True
        except Exception as e:
            _flog(f"OCR: EasyOCR 加载失败: {e}")

        return False

    # ── 引擎工厂（创建并缓存） ──

    def _create_windows_ocr(self):
        """创建 Windows OCR 引擎实例

        使用 winrt 的 OcrEngine，优先中文（zh-CN），
        降级到用户配置文件语言。
        """
        try:
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.globalization import Language

            # 优先尝试中文
            cn = Language("zh-CN")
            if OcrEngine.is_language_supported(cn):
                return OcrEngine.try_create_from_language(cn)

            # 降级：使用用户配置文件的默认语言
            return OcrEngine.try_create_from_user_profile_languages()
        except Exception:
            return None

    @staticmethod
    def _create_easyocr():
        """创建 EasyOCR 阅读器实例"""
        import warnings
        warnings.filterwarnings("ignore")
        import easyocr
        return easyocr.Reader(["ch_sim", "en"], gpu=False)

    # ── 识别 ──

    def scan(
        self, img: np.ndarray, min_conf: float = 0.3
    ) -> List[OCRResult]:
        """对图像执行 OCR 识别

        参数:
            img:      BGR 格式的 numpy 数组
            min_conf: 最低置信度阈值（仅 EasyOCR 使用）

        返回:
            [(center_x, center_y, text, confidence), ...] 列表
        """
        if self._engine is None and not self.init():
            return []

        try:
            if self._engine_type == "windows":
                return self._recognize_windows(img)
            else:
                return self._recognize_easyocr(img, min_conf)
        except Exception as e:
            _flog(f"OCR 扫描异常: {e}")
            # 异常时重置引擎，下次重新初始化
            self._engine = None
            self._status = "异常"
            return []

    def _recognize_windows(self, img: np.ndarray) -> List[OCRResult]:
        """使用 Windows OCR 引擎识别（同步方式，避免 event loop 冲突）

        先尝试原始图像（仅放大），若无结果则用游戏字体预处理。
        """
        if cv2 is None:
            return []

        h, w = img.shape[:2]
        if h < 10 or w < 10 or img.std() < 5:
            return []

        # 策略 1：原始图像 + 放大
        proc = img.copy()
        scale1 = 1.0
        if max(w, h) < 500:
            scale1 = 500.0 / max(w, h)
            proc = cv2.resize(
                proc, None, fx=scale1, fy=scale1, interpolation=cv2.INTER_CUBIC
            )
        h1, w1 = proc.shape[:2]
        results = self._do_ocr_windows(proc, w1, h1)
        if results and scale1 != 1.0:
            results = [
                (int(cx / scale1), int(cy / scale1), t, conf)
                for cx, cy, t, conf in results
            ]

        # 策略 2：无结果 → 游戏字体预处理
        if not results:
            proc2 = OCR._preprocess_game_font(img)
            h2, w2 = proc2.shape[:2]
            results = self._do_ocr_windows(proc2, w2, h2)
            if results:
                orig_h, orig_w = img.shape[:2]
                scale2_x = orig_w / w2
                scale2_y = orig_h / h2
                results = [
                    (int(cx * scale2_x), int(cy * scale2_y), t, conf)
                    for cx, cy, t, conf in results
                ]

        return results

    def _do_ocr_windows(
        self, img: np.ndarray, w: int, h: int
    ) -> List[OCRResult]:
        """对预处理后的图像执行 Windows OCR（同步调用）"""
        try:
            from winrt.windows.graphics.imaging import (
                SoftwareBitmap,
                BitmapPixelFormat,
            )

            # BGRA 格式
            rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            bmp = SoftwareBitmap.create_copy_from_buffer(
                rgba.tobytes(), BitmapPixelFormat.RGBA8, w, h
            )

            # 同步调用：recognize_async(...).get() 阻塞等待结果
            result = self._engine.recognize_async(bmp).get()
            if not result or not result.lines:
                return []

            out = []
            for line in result.lines:
                text = line.text.strip()
                if not text:
                    continue
                cx, cy = self._extract_line_center(line, w, h)
                out.append((cx, cy, text, 1.0))
            return out
        except Exception:
            return []

    @staticmethod
    def _extract_line_center(line, img_w: int, img_h: int) -> Tuple[int, int]:
        """提取文本行的中心坐标"""
        # 尝试从 bounding_rect 获取
        for attr_name in (
            "bounding_rect", "bounding_rectangle",
            "BoundingRect", "BoundingRectangle",
        ):
            try:
                bb = getattr(line, attr_name, None)
                if bb is not None:
                    x = getattr(bb, "x", getattr(bb, "X", 0))
                    y = getattr(bb, "y", getattr(bb, "Y", 0))
                    w = getattr(bb, "width", getattr(bb, "Width", 0))
                    h = getattr(bb, "height", getattr(bb, "Height", 0))
                    return int(x + w / 2), int(y + h / 2)
            except Exception:
                continue

        # 降级：从 words 计算包围盒
        try:
            words = list(line.words)
            if words:
                xs, ys = [], []
                for word in words:
                    for wa in ("bounding_rect", "bounding_rectangle", "BoundingRect"):
                        try:
                            wb = getattr(word, wa, None)
                            if wb is not None:
                                wx = getattr(wb, "x", getattr(wb, "X", 0))
                                wy = getattr(wb, "y", getattr(wb, "Y", 0))
                                ww = getattr(wb, "width", getattr(wb, "Width", 0))
                                wh = getattr(wb, "height", getattr(wb, "Height", 0))
                                xs.extend([wx, wx + ww])
                                ys.extend([wy, wy + wh])
                                break
                        except Exception:
                            continue
                if xs and ys:
                    return int((min(xs) + max(xs)) / 2), int((min(ys) + max(ys)) / 2)
        except Exception:
            pass

        # 最终降级：图像中心
        return img_w // 2, img_h // 2

    def _recognize_easyocr(
        self, img: np.ndarray, min_conf: float
    ) -> List[OCRResult]:
        """使用 EasyOCR 识别"""
        if cv2 is None:
            return []

        try:
            proc = OCR._preprocess_game_font(img)
            rgb = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
            results = []
            for box, text, conf in self._engine.readtext(rgb):
                if conf < min_conf:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                cx = int(sum(xs) / len(xs))
                cy = int(sum(ys) / len(ys))
                results.append((cx, cy, text.strip(), conf))
            return results
        except Exception as e:
            _flog(f"EasyOCR 异常: {e}")
            return []

    # ── 图像预处理 ──

    @staticmethod
    def _preprocess_game_font(img: np.ndarray) -> np.ndarray:
        """游戏字体 OCR 预处理

        处理步骤：放大 → 灰度 → OTSU 二值化 → 形态学闭运算
        用于去除游戏文字的抗锯齿、描边、阴影等效果。
        """
        if cv2 is None:
            return img

        h, w = img.shape[:2]
        # 放大小字以提高识别率
        if max(w, h) < 500:
            scale = 500.0 / max(w, h)
            img = cv2.resize(
                img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
            )

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(
            blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)

    # ── 配置 ──

    def set_preferred(self, engine_type: str) -> None:
        """切换首选 OCR 引擎（"windows" 或 "easyocr"）"""
        if engine_type not in ("windows", "easyocr"):
            return
        self._preferred = engine_type
        self._engine = None
        self._engine_type = None
        self._status = "未加载"
        try:
            from core.config import save_config
            save_config(preferred_ocr_engine=engine_type)
        except Exception:
            pass

    def load_preferred(self) -> None:
        """从配置文件加载首选引擎"""
        try:
            from core.config import load_config
            v = load_config().get("preferred_ocr_engine", "windows")
            self._preferred = v if v in ("windows", "easyocr") else "windows"
        except Exception:
            self._preferred = "windows"

    @staticmethod
    def find_text(
        target: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        timeout: float = 5.0,
        min_conf: float = 0.3,
        hwnd: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        """在屏幕上查找指定文字并返回位置

        参数:
            target:   目标文字，支持 "|" 分隔多个候选
            region:   (x, y, w, h) 搜索区域，None 为全屏
            timeout:  最大搜索时间（秒）
            min_conf: 最低置信度
            hwnd:     目标窗口句柄（后台模式）

        返回:
            (x, y) 文字中心坐标，未找到返回 None
        """
        from engine.vision.screenshot import Screenshot

        ocr = OCR.instance()
        if ocr._engine is None and not ocr.init():
            return None

        # 解析多个候选目标
        targets = [t.strip() for t in target.split("|") if t.strip()]
        if not targets:
            return None
        clean_targets = [t.replace(" ", "") for t in targets]

        deadline = time.time() + timeout
        while time.time() < deadline:
            img = Screenshot.capture(region, hwnd)
            if img is None:
                time.sleep(0.3)
                continue

            results = ocr.scan(img, min_conf * 0.5)
            for cx, cy, txt, _ in results:
                txt_clean = txt.replace(" ", "")
                for i, t in enumerate(targets):
                    if t in txt or clean_targets[i] in txt_clean:
                        if region:
                            cx += region[0]
                            cy += region[1]
                        return (cx, cy)

            time.sleep(0.1)

        return None
