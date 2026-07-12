"""
截图服务

支持：
- 全屏截图
- 区域截图
- 窗口截图
- base64 编码输出

优先使用 mss（高性能），降级到 pyautogui。
"""

import numpy as np

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class ScreenshotService:
    """
    截图服务

    用法:
        svc = ScreenshotService()
        img = svc.capture_fullscreen()
        b64 = svc.to_base64(img)
    """

    def __init__(self):
        self._mss_instance = None

    def capture_fullscreen(self) -> np.ndarray | None:
        """
        全屏截图

        Returns:
            numpy array (BGR 格式)
        """
        if HAS_MSS:
            return self._capture_mss_fullscreen()
        elif HAS_PYAUTOGUI:
            return self._capture_pyautogui_fullscreen()
        else:
            raise RuntimeError("截图需要安装 mss 或 pyautogui")

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray | None:
        """
        区域截图

        Args:
            x, y: 左上角坐标
            w, h: 宽高

        Returns:
            numpy array (BGR 格式)
        """
        import cv2
        full = self.capture_fullscreen()
        if full is None:
            return None
        return full[y:y + h, x:x + w]

    def capture_window(self, hwnd: int) -> np.ndarray | None:
        """
        窗口截图（截取指定窗口句柄的画面）

        优先使用 Win32 PrintWindow，降级为全屏截图后裁剪。

        Args:
            hwnd: 窗口句柄

        Returns:
            numpy array (BGR 格式)
        """
        try:
            import win32gui
            import win32ui
            import win32con

            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            w, h = rect[2] - rect[0], rect[3] - rect[1]

            if w <= 0 or h <= 0:
                return None

            # 尝试 PrintWindow
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)

            result = win32gui.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)

            if result == 1:
                # PrintWindow 成功
                bmp_info = bitmap.GetInfo()
                bmp_bits = bitmap.GetBitmapBits(True)

                img = np.frombuffer(bmp_bits, dtype=np.uint8)
                img = img.reshape((bmp_info["bmHeight"], bmp_info["bmWidth"], 4))
                # BGRA → BGR
                import cv2
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                # PrintWindow 失败，降级为区域截图
                img = self.capture_region(x, y, w, h)

            # 清理 GDI 资源
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return img

        except ImportError:
            # 无 pywin32，降级为全屏截图
            return self.capture_fullscreen()

    def to_base64(self, img: np.ndarray, format: str = ".png") -> str:
        """截图转 base64 字符串"""
        import base64
        import cv2
        _, buf = cv2.imencode(format, img)
        return base64.b64encode(buf).decode("utf-8")

    @staticmethod
    def save(img: np.ndarray, path: str):
        """保存截图到文件"""
        import cv2
        cv2.imwrite(path, img)

    # ── 内部实现 ───────────────────

    def _capture_mss_fullscreen(self) -> np.ndarray:
        """mss 截图（快速）"""
        import cv2
        if self._mss_instance is None:
            self._mss_instance = mss.mss()
        monitor = self._mss_instance.monitors[0]  # 主显示器
        sct_img = self._mss_instance.grab(monitor)
        img = np.array(sct_img)
        # BGRA → BGR
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    @staticmethod
    def _capture_pyautogui_fullscreen() -> np.ndarray:
        """pyautogui 截图（降级方案）"""
        import cv2
        img = pyautogui.screenshot()
        # RGB → BGR
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
