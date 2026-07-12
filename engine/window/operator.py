"""
窗口操作服务

支持：
- 获取窗口信息（位置、大小、标题、类名、状态）
- 将窗口置顶并激活
- 移动并调整窗口大小
- 最小化 / 恢复
- 检查窗口是否仍然存在

依赖：pywin32
"""

import time

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class WindowOperator:
    """
    窗口操作器

    用法:
        op = WindowOperator()
        info = op.get_window_info(hwnd)
        op.set_foreground(hwnd)
        op.move_window(hwnd, 100, 100, 800, 600)
    """

    def __init__(self):
        if not HAS_WIN32:
            raise RuntimeError("窗口操作需要安装 pywin32")
        self.current_hwnd: int = 0

    def get_window_info(self, hwnd: int) -> dict | None:
        """
        获取窗口的完整信息

        Args:
            hwnd: 窗口句柄

        Returns:
            包含位置、大小、标题、类名的字典
        """
        try:
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            placement = win32gui.GetWindowPlacement(hwnd)

            is_visible = win32gui.IsWindowVisible(hwnd)
            is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED

            return {
                "hwnd": hwnd,
                "title": title,
                "class_name": class_name,
                "x": rect[0],
                "y": rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
                "is_visible": is_visible,
                "is_minimized": is_minimized,
                "is_maximized": is_maximized,
            }
        except Exception:
            return None

    def set_foreground(self, hwnd: int) -> bool:
        """
        将窗口置顶并激活

        Args:
            hwnd: 窗口句柄

        Returns:
            bool: 操作是否成功
        """
        try:
            # 如果最小化，先恢复
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            win32gui.SetForegroundWindow(hwnd)
            self.current_hwnd = hwnd
            time.sleep(0.05)  # 等待窗口切换
            return True
        except Exception:
            return False

    def move_window(self, hwnd: int, x: int, y: int, w: int, h: int) -> bool:
        """
        移动窗口并调整大小

        Args:
            hwnd: 窗口句柄
            x, y: 新位置
            w, h: 新尺寸

        Returns:
            bool: 是否成功
        """
        try:
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            return True
        except Exception:
            return False

    def minimize(self, hwnd: int) -> bool:
        """最小化窗口"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            return False

    def restore(self, hwnd: int) -> bool:
        """恢复窗口（从最小化或最大化）"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception:
            return False

    def maximize(self, hwnd: int) -> bool:
        """最大化窗口"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception:
            return False

    def close(self, hwnd: int) -> bool:
        """关闭窗口（发送 WM_CLOSE）"""
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False

    def is_window_alive(self, hwnd: int) -> bool:
        """检查窗口是否仍然存在"""
        try:
            return win32gui.IsWindow(hwnd)
        except Exception:
            return False

    def get_foreground_hwnd(self) -> int:
        """获取当前前台窗口句柄"""
        try:
            return win32gui.GetForegroundWindow()
        except Exception:
            return 0
