"""视觉子系统 - 截图功能

支持三种截图方式：
1. Win32 GDI BitBlt（零拷贝，最快，前台窗口）
2. PrintWindow（后台窗口截图）
3. mss / pyautogui（降级方案）
"""

import base64
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

import numpy as np

# ── 可选依赖 ──
try:
    import win32gui
    import win32con
    _HAS_W32 = True
except ImportError:
    _HAS_W32 = False

try:
    import mss as _mss_lib
    _SCT = _mss_lib.mss()
except Exception:
    _SCT = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

# ── Win32 GDI 辅助结构 ──


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


# ── 工具函数 ──


def _array_to_base64(img: np.ndarray, fmt: str = ".png") -> str:
    """将 numpy 图像数组编码为 base64 字符串"""
    if cv2 is None:
        raise RuntimeError("opencv-python 未安装，无法编码图像")
    _, buf = cv2.imencode(fmt, img)
    return base64.b64encode(buf).decode("ascii")


def _array_to_data_uri(img: np.ndarray, fmt: str = ".png") -> str:
    """将 numpy 图像数组编码为 data URI"""
    b64 = _array_to_base64(img, fmt)
    mime = "image/png" if fmt == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


# ══ 截图 ══


class Screenshot:
    """截图服务

    用法:
        img = Screenshot.capture()              # 全屏截图
        img = Screenshot.capture(region=(0,0,100,100))  # 区域截图
        img = Screenshot.capture(hwnd=12345)    # 窗口截图
        b64 = Screenshot.to_base64(img)         # 转 base64
        uri = Screenshot.to_data_uri(img)       # 转 data URI
    """

    # ── 公共 API ──

    @staticmethod
    def capture(
        region: Optional[Tuple[int, int, int, int]] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[np.ndarray]:
        """截取屏幕或窗口

        参数:
            region: (x, y, w, h) 区域坐标，None 为全屏
            hwnd:   目标窗口句柄，None 为前台屏幕

        返回:
            BGR 格式的 numpy 数组 (H, W, 3)，失败返回 None
        """
        # 后台截图路径：PrintWindow
        if hwnd and _HAS_W32:
            img = Screenshot._capture_window(hwnd)
            if img is not None and img.size > 0 and img.mean() > 2 and img.std() > 3:
                return img

        # 前台截图路径：优先 GDI BitBlt
        img = Screenshot._capture_gdi(region)
        if img is not None:
            return img

        # 降级：mss
        img = Screenshot._capture_mss(region)
        if img is not None:
            return img

        # 最后降级：pyautogui
        return Screenshot._capture_pyautogui(region)

    @staticmethod
    def capture_full() -> Optional[np.ndarray]:
        """全屏截图快捷方法"""
        return Screenshot.capture()

    @staticmethod
    def capture_region(
        x: int, y: int, w: int, h: int
    ) -> Optional[np.ndarray]:
        """区域截图快捷方法"""
        return Screenshot.capture(region=(x, y, w, h))

    @staticmethod
    def capture_window(hwnd: int) -> Optional[np.ndarray]:
        """窗口截图快捷方法"""
        return Screenshot.capture(hwnd=hwnd)

    @staticmethod
    def to_base64(img: np.ndarray, fmt: str = ".png") -> str:
        """将图像数组编码为 base64 字符串"""
        return _array_to_base64(img, fmt)

    @staticmethod
    def to_data_uri(img: np.ndarray, fmt: str = ".png") -> str:
        """将图像数组编码为 data URI"""
        return _array_to_data_uri(img, fmt)

    # ── 内部实现 ──

    @staticmethod
    def _capture_gdi(
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[np.ndarray]:
        """Win32 GDI BitBlt 零拷贝截图"""
        if cv2 is None:
            return None
        try:
            if region:
                x, y, w, h = region
            else:
                x, y = 0, 0
                w = ctypes.windll.user32.GetSystemMetrics(0)
                h = ctypes.windll.user32.GetSystemMetrics(1)

            if w <= 0 or h <= 0:
                return None

            hdc_screen = None
            hdc_mem = None
            bmp = None
            try:
                hdc_screen = ctypes.windll.user32.GetDC(None)
                hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
                bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
                ctypes.windll.gdi32.SelectObject(hdc_mem, bmp)
                ctypes.windll.gdi32.BitBlt(
                    hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020
                )

                buf = ctypes.create_string_buffer(w * h * 4)
                bmi = _BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
                bmi.biWidth = w
                bmi.biHeight = -h  # 负值表示自上而下
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                ctypes.windll.gdi32.GetDIBits(
                    hdc_mem, bmp, 0, h, buf, ctypes.byref(bmi), 0
                )

                arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
                return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            finally:
                # GDI 资源清理（try-finally 保护，防止泄漏）
                if bmp is not None:
                    ctypes.windll.gdi32.DeleteObject(bmp)
                if hdc_mem is not None:
                    ctypes.windll.gdi32.DeleteDC(hdc_mem)
                if hdc_screen is not None:
                    ctypes.windll.user32.ReleaseDC(None, hdc_screen)
        except Exception:
            return None

    @staticmethod
    def _capture_window(hwnd: int) -> Optional[np.ndarray]:
        """PrintWindow 后台窗口截图"""
        if not _HAS_W32 or cv2 is None:
            return None

        hwnd_dc = None
        mfc_dc = None
        hbitmap = None
        old_bmp = None
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if w < 16 or h < 16:
                return None

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32gui.CreateCompatibleDC(hwnd_dc)
            hbitmap = win32gui.CreateCompatibleBitmap(hwnd_dc, w, h)
            old_bmp = win32gui.SelectObject(mfc_dc, hbitmap)
            ctypes.windll.user32.PrintWindow(
                ctypes.c_void_p(hwnd), ctypes.c_void_p(mfc_dc), 0
            )

            buf = ctypes.create_string_buffer(w * h * 4)
            bmi = _BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            ctypes.windll.gdi32.GetDIBits(
                mfc_dc, hbitmap, 0, h, buf, ctypes.byref(bmi), 0
            )

            arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        except Exception:
            return None
        finally:
            # GDI 资源清理
            try:
                if old_bmp is not None and mfc_dc is not None:
                    win32gui.SelectObject(mfc_dc, old_bmp)
                if hbitmap is not None:
                    win32gui.DeleteObject(hbitmap)
                if mfc_dc is not None:
                    win32gui.DeleteDC(mfc_dc)
                if hwnd_dc is not None and hwnd is not None:
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
            except Exception:
                pass

    @staticmethod
    def _capture_mss(
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[np.ndarray]:
        """mss 截图（支持直接区域截取）"""
        if _SCT is None:
            return None
        try:
            if region:
                x, y, w, h = region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                monitor = _SCT.monitors[0]  # 全屏
            img = _SCT.grab(monitor)
            arr = np.array(img)
            # mss 返回 BGRA，转为 BGR
            if arr.shape[2] == 4:
                arr = arr[:, :, :3]
            return arr
        except Exception:
            return None

    @staticmethod
    def _capture_pyautogui(
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[np.ndarray]:
        """pyautogui 截图（最后降级方案）"""
        if pyautogui is None:
            return None
        try:
            if region:
                x, y, w, h = region
                img = pyautogui.screenshot(region=(x, y, w, h))
            else:
                img = pyautogui.screenshot()
            arr = np.array(img)
            # PIL 返回 RGB，转为 BGR
            if arr.shape[2] == 3:
                arr = arr[:, :, ::-1]
            return arr
        except Exception:
            return None
