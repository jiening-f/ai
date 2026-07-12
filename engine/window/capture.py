"""
窗口截图服务

使用 Win32 API 截取指定窗口内容（即使被遮挡）。

方案：
1. PrintWindow — 主要方式，截取窗口内容（即使被遮挡）
2. BitBlt — 备用方案（需要窗口可见）
3. 区域截图 — 最终降级方案（激活窗口后用 pyautogui 截区域）
"""

import numpy as np

try:
    import win32gui
    import win32ui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class WindowCapture:
    """
    窗口截图器

    用法:
        cap = WindowCapture()
        img = cap.capture(hwnd)
        # 或先用 detector 找到窗口
        img = cap.capture_by_title("记事本")
    """

    def __init__(self):
        if not HAS_WIN32:
            raise RuntimeError("窗口截图需要安装 pywin32")

    def capture(self, hwnd: int) -> np.ndarray | None:
        """
        截取指定窗口

        优先使用 PrintWindow，失败则降级为 BitBlt → 区域截图

        Args:
            hwnd: 窗口句柄

        Returns:
            numpy array (BGR) 或 None
        """
        # 方法 1：PrintWindow
        img = self._capture_printwindow(hwnd)
        if img is not None:
            return img

        # 方法 2：BitBlt
        img = self._capture_bitblt(hwnd)
        if img is not None:
            return img

        # 方法 3：区域截图降级
        return self._capture_region_fallback(hwnd)

    def capture_by_title(self, title: str) -> np.ndarray | None:
        """根据窗口标题查找并截图"""
        from engine.window.detector import WindowDetector
        detector = WindowDetector()
        win = detector.find_one(title)
        if win:
            return self.capture(win.hwnd)
        return None

    # ── 内部实现 ───────────────────

    @staticmethod
    def _capture_printwindow(hwnd: int) -> np.ndarray | None:
        """PrintWindow 方式截图（可截取被遮挡窗口）"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]

            if w <= 0 or h <= 0:
                return None

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)

            # PW_RENDERFULLCONTENT = 2 (Win8+)，兼容方案：先尝试 2，失败则用 0
            result = 0
            for pw_flag in (2, 0):
                try:
                    result = win32gui.PrintWindow(hwnd, save_dc.GetSafeHdc(), pw_flag)
                    if result == 1:
                        break
                except Exception:
                    continue

            img = None
            if result == 1:
                bmp_bits = bitmap.GetBitmapBits(True)
                img = np.frombuffer(bmp_bits, dtype=np.uint8)
                img = img.reshape((h, w, 4))
                # BGRA → BGR
                import cv2
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 清理 GDI 资源
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return img
        except Exception:
            return None

    @staticmethod
    def _capture_bitblt(hwnd: int) -> np.ndarray | None:
        """BitBlt 方式截图（需要窗口可见）"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]

            if w <= 0 or h <= 0:
                return None

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

            bmp_bits = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmp_bits, dtype=np.uint8)
            img = img.reshape((h, w, 4))
            import cv2
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 清理
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return img
        except Exception:
            return None

    @staticmethod
    def _capture_region_fallback(hwnd: int) -> np.ndarray | None:
        """区域截图降级方案"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if w <= 0 or h <= 0:
                return None

            import pyautogui
            import cv2
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception:
            return None
