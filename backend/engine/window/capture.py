"""窗口截图 — 使用 Win32 API 截取指定窗口内容"""
import ctypes
from ctypes import wintypes
import time
from typing import Optional

import numpy as np

from core.constants import _flog

# ── 可选依赖 ────────────────────────────────────
try:
    import win32gui
    import win32con
    import win32ui
    import win32api
    _HAS_W32 = True
except ImportError:
    _HAS_W32 = False

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

# 声明 PrintWindow API 参数类型
_PW_RENDERFULLCONTENT = 2
try:
    ctypes.windll.user32.PrintWindow.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint
    ]
    ctypes.windll.user32.PrintWindow.restype = ctypes.c_bool
except Exception:
    pass


# ══ GDI 辅助结构 ══════════════════════════════════

class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          wintypes.DWORD),
        ("biWidth",         ctypes.c_int32),
        ("biHeight",        ctypes.c_int32),
        ("biPlanes",        wintypes.WORD),
        ("biBitCount",      wintypes.WORD),
        ("biCompression",   wintypes.DWORD),
        ("biSizeImage",     wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed",       wintypes.DWORD),
        ("biClrImportant",  wintypes.DWORD),
    ]


# ══ 私有 Win32 截图封装 ════════════════════════════

def _win32_printwindow(hwnd: int) -> Optional[np.ndarray]:
    """使用 PrintWindow API 截取窗口内容（即使窗口被遮挡）
    返回 BGR 格式的 numpy 数组
    """
    if not _HAS_W32 or not hwnd:
        return None

    hwnd_dc = mfc_dc = hbitmap = old_bmp = None
    try:
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w < 16 or h < 16:
            return None

        # 创建兼容 DC 和位图
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        hbitmap = win32ui.CreateBitmap()
        hbitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        old_bmp = save_dc.SelectObject(hbitmap)

        # PrintWindow：截取窗口内容
        result = ctypes.windll.user32.PrintWindow(
            ctypes.c_void_p(hwnd),
            ctypes.c_void_p(save_dc.GetSafeHdc()),
            _PW_RENDERFULLCONTENT,
        )

        if not result:
            # 降级：不带 PW_RENDERFULLCONTENT 标志重试
            result = ctypes.windll.user32.PrintWindow(
                ctypes.c_void_p(hwnd),
                ctypes.c_void_p(save_dc.GetSafeHdc()),
                0,
            )

        # 从位图提取像素数据
        bmp_info = hbitmap.GetInfo()
        bmp_bits = hbitmap.GetBitmapBits(True)
        arr = np.frombuffer(bmp_bits, dtype=np.uint8).reshape(h, w, 4)

        # BGRA → BGR
        if _HAS_CV2:
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            return arr[..., :3]

    except Exception as e:
        _flog(f"PrintWindow 截图异常: {e}")
        return None
    finally:
        try:
            if old_bmp:
                save_dc.SelectObject(old_bmp)
            if hbitmap:
                win32gui.DeleteObject(hbitmap.GetHandle())
            if save_dc:
                save_dc.DeleteDC()
            if mfc_dc:
                mfc_dc.DeleteDC()
            if hwnd_dc and hwnd:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass


def _win32_gdi_region(x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
    """使用 GDI BitBlt + GetDIBits 截取屏幕区域
    返回 BGR 格式的 numpy 数组，零中间转换
    """
    hdc_screen = hdc_mem = bmp = None
    try:
        hdc_screen = ctypes.windll.user32.GetDC(None)
        hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
        bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        ctypes.windll.gdi32.SelectObject(hdc_mem, bmp)
        # SRCCOPY = 0x00CC0020
        ctypes.windll.gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)

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
        if _HAS_CV2:
            result = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            result = arr[..., :3]

        return result
    except Exception as e:
        _flog(f"GDI 区域截图异常: {e}")
        return None
    finally:
        try:
            if bmp:
                ctypes.windll.gdi32.DeleteObject(bmp)
        except Exception:
            pass
        try:
            if hdc_mem:
                ctypes.windll.gdi32.DeleteDC(hdc_mem)
        except Exception:
            pass
        try:
            if hdc_screen:
                ctypes.windll.user32.ReleaseDC(None, hdc_screen)
        except Exception:
            pass


def _win32_get_window_rect(hwnd: int) -> Optional[tuple]:
    """获取窗口矩形 (x, y, w, h)"""
    try:
        x1, y1, x2, y2 = win32gui.GetWindowRect(hwnd)
        return (x1, y1, x2 - x1, y2 - y1)
    except Exception:
        return None


# ══ 窗口截图器 ═════════════════════════════════════

class WindowCapture:
    """窗口截图

    使用 Win32 API 截取指定窗口的内容。
    优先使用 PrintWindow（即使被遮挡也能截取），
    失败时降级为激活窗口 + GDI 区域截图。
    """

    @staticmethod
    def capture_window(hwnd: int) -> Optional[np.ndarray]:
        """截取指定窗口的完整内容
        策略:
        1. 先尝试 PrintWindow（被遮挡也能截到）
        2. 降级：激活窗口后用 GDI 区域截图
        Args:
            hwnd: 目标窗口句柄
        Returns:
            BGR 格式的 numpy 数组，失败返回 None
        """
        if not _HAS_W32 or not hwnd:
            _flog("窗口截图: pywin32 未安装或无窗口句柄")
            return None

        # 检查窗口是否存活
        try:
            if not win32gui.IsWindow(hwnd):
                _flog(f"窗口截图: 句柄 {hwnd} 已失效")
                return None
        except Exception:
            return None

        # 策略1: PrintWindow（后台截图，即使被遮挡）
        img = _win32_printwindow(hwnd)
        if img is not None and img.size > 100:
            # 检查图像是否有内容（非纯黑/纯白）
            if img.mean() > 2 and img.std() > 3:
                return img

        # 策略2: 降级 — 激活窗口后 GDI 区域截图
        _flog("PrintWindow 截图质量不足，降级为前台区域截图")
        rect = _win32_get_window_rect(hwnd)
        if not rect:
            return None

        x, y, w, h = rect

        # 尝试激活窗口以确保内容可见
        try:
            from engine.window.operator import WindowOperator
            WindowOperator.set_foreground(hwnd)
            time.sleep(0.15)
        except Exception:
            pass

        # GDI 区域截图
        img = _win32_gdi_region(x, y, w, h)
        if img is not None:
            return img

        # 策略3: pyautogui 降级
        if _HAS_PYAUTOGUI:
            try:
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                img = np.array(screenshot)
                if _HAS_CV2:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                return img
            except Exception as e:
                _flog(f"pyautogui 截图异常: {e}")

        _flog(f"窗口截图: 所有策略均失败")
        return None

    @staticmethod
    def capture_region(hwnd: int, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        """截取窗口内的指定区域（相对窗口左上角的坐标）
        Args:
            hwnd: 窗口句柄
            x, y: 区域内相对坐标（相对窗口左上角）
            w, h: 区域宽高
        Returns:
            BGR 格式的 numpy 数组
        """
        rect = _win32_get_window_rect(hwnd)
        if not rect:
            return None

        abs_x = rect[0] + x
        abs_y = rect[1] + y

        # 先尝试全窗口 PrintWindow，再裁剪区域
        full = _win32_printwindow(hwnd)
        if full is not None and full.size > 100:
            fh, fw = full.shape[:2]
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(fw, x + w), min(fh, y + h)
            if x2 > x1 and y2 > y1:
                return full[y1:y2, x1:x2]

        # 降级：GDI 区域截图
        return _win32_gdi_region(abs_x, abs_y, w, h)


# ── 便捷函数 ────────────────────────────────────
capture_window = WindowCapture.capture_window
capture_region = WindowCapture.capture_region
