"""业务逻辑层 - 视觉服务：截图/OCR/模板匹配"""
import os, time, threading, ctypes
from ctypes import wintypes
from typing import Optional
import numpy as np
from PIL import Image

from core.constants import TEMPLATE_DIR, _flog
from core.cache import CacheManager

# 声明 PrintWindow API 类型（避免调用时类型转换错误）
_PW_RENDERFULLCONTENT = 2
try:
    ctypes.windll.user32.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    ctypes.windll.user32.PrintWindow.restype = ctypes.c_bool
except: pass

# 可选依赖
try:
    import win32gui, win32con, win32api
    _HAS_W32 = True
except: _HAS_W32 = False

try:
    from mss import MSS as mss
    _SCT = mss()
except: _SCT = None

try:
    import cv2
except: cv2 = None

try:
    import pyautogui
except: pyautogui = None


# ══ Win32 GDI 辅助结构 ═══════════════════════

class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          ctypes.c_uint32),
        ("biWidth",         ctypes.c_int32),
        ("biHeight",        ctypes.c_int32),
        ("biPlanes",        ctypes.c_uint16),
        ("biBitCount",      ctypes.c_uint16),
        ("biCompression",   ctypes.c_uint32),
        ("biSizeImage",     ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed",       ctypes.c_uint32),
        ("biClrImportant",  ctypes.c_uint32),
    ]


# ══ 截图 ═════════════════════════════════════

class Screenshot:
    @staticmethod
    def capture(region=None, hwnd=None):
        # 后台截图：PrintWindow 优先
        if hwnd and _HAS_W32:
            img = Screenshot._printwindow(hwnd)
            if img is not None and img.mean() > 2 and img.std() > 3:
                return img
        # ── 前台截图：GDI 零拷贝优先（比 mss/pyautogui 快 3-10 倍）──
        for _ in range(2):
            img = None
            try:
                if region:
                    img = Screenshot._gdi_region(region[0], region[1], region[2], region[3])
                else:
                    img = Screenshot._gdi_region(0, 0,
                        ctypes.windll.user32.GetSystemMetrics(0),
                        ctypes.windll.user32.GetSystemMetrics(1))
            except Exception as e:
                _flog(f"GDI截图异常: {e}")
            if img is not None:
                return img
        return None

    @staticmethod
    def _gdi_region(x, y, w, h):
        """原生 Win32 GDI 截图 — BitBlt + GetDIBits 直接填 numpy，零中间转换"""
        hdc_screen = ctypes.windll.user32.GetDC(None)
        hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
        bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        ctypes.windll.gdi32.SelectObject(hdc_mem, bmp)
        ctypes.windll.gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)

        buf = ctypes.create_string_buffer(w * h * 4)
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        ctypes.windll.gdi32.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)

        arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
        result = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR) if cv2 else arr[...,:3]

        ctypes.windll.gdi32.DeleteObject(bmp)
        ctypes.windll.gdi32.DeleteDC(hdc_mem)
        ctypes.windll.user32.ReleaseDC(None, hdc_screen)
        return result

    @staticmethod
    def _printwindow(hwnd):
        hwnd_dc = mfc_dc = hbitmap = old = None
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            if w < 16 or h < 16: return None
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32gui.CreateCompatibleDC(hwnd_dc)
            hbitmap = win32gui.CreateCompatibleBitmap(hwnd_dc, w, h)
            old = win32gui.SelectObject(mfc_dc, hbitmap)
            ctypes.windll.user32.PrintWindow(ctypes.c_void_p(hwnd),
                                             ctypes.c_void_p(mfc_dc), 0)
            # ── 零拷贝 numpy，跳过 PIL ──
            buf = ctypes.create_string_buffer(w * h * 4)
            bmi = _BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            ctypes.windll.gdi32.GetDIBits(mfc_dc, hbitmap, 0, h, buf, ctypes.byref(bmi), 0)
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR) if cv2 else arr[...,:3]
        except Exception as e:
            _flog(f"后台截图(PrintWindow)不可用，已切换到前台截图: {e}")
            return None
        finally:
            try:
                if old and mfc_dc: win32gui.SelectObject(mfc_dc, old)
                if hbitmap: win32gui.DeleteObject(hbitmap)
                if mfc_dc: win32gui.DeleteDC(mfc_dc)
                if hwnd_dc and hwnd: win32gui.ReleaseDC(hwnd, hwnd_dc)
            except: pass

    @staticmethod
    def capture_template(delay=3):
        if pyautogui is None: return None
        time.sleep(delay)
        x, y = pyautogui.position()
        return Screenshot.capture((x-45, y-22, 90, 44))


# ══ OCR ════════════════════════════════════════

class OCR:
    _inst: Optional['OCR'] = None

    def __init__(self):
        self.engine = None
        self.status = "未加载"
        self.engine_type: Optional[str] = None
        self.preferred = "windows"
        self._lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls._inst is None: cls._inst = cls()
        return cls._inst

    def _create_windows(self):
        try:
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.globalization import Language
            cn = Language("zh-CN")
            return OcrEngine.try_create_from_language(cn) if OcrEngine.is_language_supported(cn) else None
        except: return None

    def _create_easyocr(self):
        import easyocr, warnings; warnings.filterwarnings('ignore')
        return easyocr.Reader(['ch_sim','en'], gpu=False)

    def init(self):
        if self.engine: return True
        with self._lock:
            if self.engine: return True
            self.status = "加载中..."
            engines = [self.preferred]
            engines.append("easy" if self.preferred == "windows" else "windows")
            for et in engines:
                if et == "windows":
                    _flog("OCR: 尝试 Windows OCR...")
                    try:
                        eng = self._create_windows()
                        if eng:
                            self.engine = eng
                            self.engine_type = "windows"
                            self.status = "Windows OCR 就绪"
                            _flog("OCR: Windows OCR 加载成功")
                            return True
                    except Exception as e:
                        _flog(f"OCR: Windows OCR 异常: {e}")
                    self.engine = None
                    _flog("OCR: Windows OCR 不可用，降级 EasyOCR")
                elif et == "easy":
                    _flog("OCR: 尝试 EasyOCR...")
                    try:
                        self.engine = self._create_easyocr()
                        self.engine_type = "easy"
                        self.status = "EasyOCR 就绪"
                        _flog("OCR: EasyOCR 加载成功")
                        return True
                    except Exception as e:
                        _flog(f"OCR: EasyOCR 加载失败: {e}")
            self.status = "OCR 失败"
            return False

    def scan(self, img, min_conf=0.3):
        if not self.engine and not self.init(): return []
        try:
            if self.engine_type == "windows": return self._scan_windows(img)
            return self._scan_easy(img, min_conf)
        except Exception as e:
            _flog(f"OCR扫描异常: {e}")
            self.engine = None; self.status = "异常"
            return []

    @staticmethod
    def _preprocess_game_font(img):
        """针对游戏字体的OCR预处理（抗锯齿/描边/阴影/非标准字形）
        步骤：放大 → 灰度 → OTSU二值化 → 形态学闭运算
        """
        h, w = img.shape[:2]
        # 放大小字
        if max(w, h) < 500:
            scale = 500.0 / max(w, h)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        # 灰度 + 高斯模糊（去锯齿）
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        # OTSU 自适应二值化（去除描边/阴影/背景纹理）
        _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # 形态学闭运算（连接断开的笔画）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        # 转回三通道（OCR 引擎需要）
        return cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)

    def _scan_windows(self, img):
        try:
            from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat
            h, w = img.shape[:2]
            if h < 10 or w < 10 or img.std() < 5: return []

            # 策略1：先试原始图像（仅放大，不做OTSU二值化）
            proc = img.copy()
            scale1 = 1.0
            if max(w, h) < 500:
                scale1 = 500.0 / max(w, h)
                proc = cv2.resize(proc, None, fx=scale1, fy=scale1, interpolation=cv2.INTER_CUBIC)
            h1, w1 = proc.shape[:2]
            out = self._do_ocr_windows(proc, w1, h1)
            # 坐标缩放回原始图像空间
            if out and scale1 != 1.0:
                out = [(int(cx / scale1), int(cy / scale1), t, conf) for cx, cy, t, conf in out]

            # 策略2：原始没结果，再用游戏字体预处理（OTSU）
            if not out:
                proc2 = OCR._preprocess_game_font(img)
                h2, w2 = proc2.shape[:2]
                out = self._do_ocr_windows(proc2, w2, h2)
                # 策略2也可能放大了图像，需要缩放回去
                if out:
                    orig_h, orig_w = img.shape[:2]
                    scale2_x = orig_w / w2
                    scale2_y = orig_h / h2
                    out = [(int(cx * scale2_x), int(cy * scale2_y), t, conf) for cx, cy, t, conf in out]

            return out
        except Exception as e:
            _flog(f"Windows OCR异常: {e}")
            return []

    def _do_ocr_windows(self, img, w, h):
        """对处理好的图像执行Windows OCR识别"""
        try:
            from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat
            rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            bmp = SoftwareBitmap.create_copy_from_buffer(rgba.tobytes(), BitmapPixelFormat.RGBA8, w, h)
            result = self.engine.recognize_async(bmp).get()
            if not result or not result.lines: return []
            out = []
            for line in result.lines:
                t = line.text.strip()
                if not t: continue
                bb = None
                for attr in ['bounding_rect', 'bounding_rectangle', 'BoundingRect', 'BoundingRectangle']:
                    try:
                        bb = getattr(line, attr)
                        if bb is not None:
                            break
                    except (AttributeError, TypeError, RuntimeError):
                        continue
                if bb is None:
                    try:
                        words = list(line.words)
                        if words:
                            xs, ys = [], []
                            for w in words:
                                wb = None
                                for wa in ['bounding_rect', 'bounding_rectangle', 'BoundingRect']:
                                    try:
                                        wb = getattr(w, wa)
                                        if wb is not None: break
                                    except: continue
                                if wb is not None:
                                    xs.append(wb.x)
                                    xs.append(wb.x + wb.width)
                                    ys.append(wb.y)
                                    ys.append(wb.y + wb.height)
                            if xs and ys:
                                cx = int((min(xs) + max(xs)) / 2)
                                cy = int((min(ys) + max(ys)) / 2)
                            else:
                                cx, cy = w // 2, h // 2
                        else:
                            cx, cy = w // 2, h // 2
                    except:
                        cx, cy = w // 2, h // 2
                else:
                    try: x_val = bb.x
                    except: x_val = getattr(bb, 'X', 0)
                    try: y_val = bb.y
                    except: y_val = getattr(bb, 'Y', 0)
                    try: w_val = bb.width
                    except: w_val = getattr(bb, 'Width', 0)
                    try: h_val = bb.height
                    except: h_val = getattr(bb, 'Height', 0)
                    cx = int(x_val + w_val / 2)
                    cy = int(y_val + h_val / 2)
                out.append((cx, cy, t, 1.0))
            return out
        except:
            return []

    def _scan_easy(self, img, min_conf):
        try:
            img = OCR._preprocess_game_font(img)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            out = []
            for box, text, conf in self.engine.readtext(rgb):
                if conf < min_conf: continue
                xs = [p[0] for p in box]; ys = [p[1] for p in box]
                out.append((int(sum(xs)/len(xs)), int(sum(ys)/len(ys)), text.strip(), conf))
            return out
        except Exception as e:
            _flog(f"EasyOCR异常: {e}")
            return []

    def set_preferred(self, et):
        self.preferred = et; self.engine = None
        self.status = "未加载"; self.engine_type = None
        from core.config import save_config
        save_config(preferred_ocr_engine=et)

    def load_preferred(self):
        from core.config import load_config
        try:
            v = load_config().get("preferred_ocr_engine", "windows")
            self.preferred = v if v in ("windows","easy") else "windows"
        except: self.preferred = "windows"

    @staticmethod
    def find_text(target, region=None, timeout=5.0, min_conf=0.3, hwnd=None):
        ocr = OCR.instance()
        if not ocr.engine and not ocr.init(): return None
        targets = [t.strip() for t in target.split("|") if t.strip()]
        if not targets: return None
        clean_targets = [t.replace(" ", "") for t in targets]
        deadline = time.time() + timeout
        retry_count = 0
        while time.time() < deadline:
            img = Screenshot.capture(region, hwnd)
            if img is None: time.sleep(0.3); continue

            results = ocr.scan(img, min_conf * 0.5)
            if results:
                for cx, cy, txt, _ in results:
                    txt_clean = txt.replace(" ", "")
                    for i, t in enumerate(targets):
                        if t in txt or clean_targets[i] in txt_clean:
                            if region: cx += region[0]; cy += region[1]
                            return (cx, cy)

            retry_count += 1
            time.sleep(0.1)
        return None


# ── 快速模式开关 ────────────────────────────
_FAST_MODE = False

def set_fast_mode(fast: bool):
    """切换快速模式/高精度模式"""
    global _FAST_MODE
    _FAST_MODE = fast
    _flog(f"模板匹配: {'快速模式' if fast else '高精度模式'}")

# ══ 模板匹配 ═════════════════════════════════

class TemplateMatcher:
    """模板匹配（形状 + 颜色双重验证）
    ═══════════════════════════════════════════
    形状相似但颜色不同的道具也能区分：
    1. CLAHE 灰度匹配 → 找形状（TM_CCOEFF_NORMED）
    2. Canny 边缘二次确认 → 排除纹理误匹配
    3. HSV 色相一致度验证 → 区分不同颜色的相似形状
    ═══════════════════════════════════════════
    道具安全：颜色验证不通过时降低置信度，
    避免将高价值道具误识别为低价值道具。
    """

    @staticmethod
    def _preprocess(img):
        """灰度 + CLAHE 标准化光照"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @staticmethod
    def _canny_edge(img):
        """Canny 边缘检测"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        return cv2.Canny(blur, 50, 150)

    @staticmethod
    def _color_similarity(template_bgr, screen_bgr, tx, ty, tw, th, scale=1.0):
        """HSV 色相一致度：比较模板与屏幕区域的色调分布
        返回 0.0~1.0 的相似度分数
        先按 scale 缩放模板，使其与匹配位置的尺寸一致
        """
        t_h, t_w = template_bgr.shape[:2]
        sw, sh = int(t_w * scale), int(t_h * scale)
        if sw < 4 or sh < 4:
            return 0.5
        tmpl_scaled = cv2.resize(template_bgr, (sw, sh),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)

        h, w = screen_bgr.shape[:2]
        x1, y1 = max(0, tx), max(0, ty)
        x2, y2 = min(w, tx + sw), min(h, ty + sh)
        if x2 - x1 < 8 or y2 - y1 < 8:
            return 0.5

        screen_roi = screen_bgr[y1:y2, x1:x2]
        screen_roi = cv2.resize(screen_roi, (sw, sh))

        tmpl_hsv = cv2.cvtColor(tmpl_scaled, cv2.COLOR_BGR2HSV)
        roi_hsv = cv2.cvtColor(screen_roi, cv2.COLOR_BGR2HSV)

        h_bins = 30
        tmpl_hist = cv2.calcHist([tmpl_hsv], [0], None, [h_bins], [0, 180])
        roi_hist = cv2.calcHist([roi_hsv], [0], None, [h_bins], [0, 180])

        cv2.normalize(tmpl_hist, tmpl_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(roi_hist, roi_hist, 0, 1, cv2.NORM_MINMAX)

        corr = cv2.compareHist(tmpl_hist, roi_hist, cv2.HISTCMP_CORREL)
        color_score = max(0.0, corr)

        for ch in [1, 2]:  # S(饱和度), V(明度)
            th = cv2.calcHist([tmpl_hsv], [ch], None, [10], [0, 256])
            rh = cv2.calcHist([roi_hsv], [ch], None, [10], [0, 256])
            cv2.normalize(th, th, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(rh, rh, 0, 1, cv2.NORM_MINMAX)
            ch_corr = cv2.compareHist(th, rh, cv2.HISTCMP_CORREL)
            color_score = min(color_score, max(0.0, ch_corr))

        return color_score

    @staticmethod
    def find(name, region=None, conf=0.72, hwnd=None):
        path = name if os.path.isfile(name) else os.path.join(TEMPLATE_DIR, f"{name}.png")
        if not os.path.isfile(path): return None
        cache = CacheManager.instance()
        template = cache.get_image(path)
        if template is None:
            try:
                template = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if template is not None:
                    cache._img_cache.put(path, template)
            except: return None
        if template is None: return None

        screen = Screenshot.capture(region, hwnd)
        if screen is None: return None

        t_h, t_w = template.shape[:2]
        s_h, s_w = screen.shape[:2]
        ref_w = region[2] if region else s_w
        scales = cache.get_scales(ref_w, t_w, t_h, fast=_FAST_MODE)
        ox = region[0] if region else 0
        oy = region[1] if region else 0

        tmpl_gray = TemplateMatcher._preprocess(template)
        scr_gray = TemplateMatcher._preprocess(screen)

        use_fast = _FAST_MODE

        best_v, best_p = 0.0, None

        for scale in scales:
            w, h = int(t_w * scale), int(t_h * scale)
            if w < 8 or h < 8 or w > s_w or h > s_h: continue

            rsz = cv2.resize(tmpl_gray, (w, h),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
            res = cv2.matchTemplate(scr_gray, rsz, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(res)

            if not use_fast and v > 0.65:
                t_edge = TemplateMatcher._canny_edge(template)
                s_edge = TemplateMatcher._canny_edge(screen)
                rsz_edge = cv2.resize(t_edge, (w, h),
                    interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
                e_res = cv2.matchTemplate(s_edge, rsz_edge, cv2.TM_CCOEFF_NORMED)
                _, ev, _, _ = cv2.minMaxLoc(e_res)
                cs = TemplateMatcher._color_similarity(
                    template, screen, loc[0], loc[1], w, h, scale)
                v = v * 0.5 + ev * 0.2 + cs * 0.3

            if v > best_v:
                best_v = v
                best_p = (loc[0] + w // 2 + ox, loc[1] + h // 2 + oy)
                if best_v >= conf:
                    break

        return best_p if best_v >= conf and best_p else None


# ── 旧接口别名 ──
tmpl_find = TemplateMatcher.find
ocr_find = OCR.find_text
_shot = Screenshot.capture
_shot_bg = Screenshot._printwindow
_init_ocr = OCR.instance().init
_init_ocr_windows = OCR.instance()._create_windows
_ocr_scan = OCR.instance().scan
