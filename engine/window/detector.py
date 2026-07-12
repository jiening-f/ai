"""
窗口检测与查找服务

支持：
- 按窗口标题模糊匹配（包含关系）
- 按窗口类名精确匹配
- 按进程名匹配
- 枚举所有可见窗口

依赖：Windows: pywin32 (win32gui + win32process)
"""

from dataclasses import dataclass, field
from typing import Callable

try:
    import win32gui
    import win32process
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    class_name: str
    rect: tuple[int, int, int, int]  # (left, top, right, bottom)
    pid: int = 0
    is_visible: bool = True
    is_minimized: bool = False

    @property
    def x(self) -> int:
        return self.rect[0]

    @property
    def y(self) -> int:
        return self.rect[1]

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def to_dict(self) -> dict:
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "class_name": self.class_name,
            "x": self.x, "y": self.y,
            "width": self.width, "height": self.height,
            "pid": self.pid,
            "is_visible": self.is_visible,
            "is_minimized": self.is_minimized,
        }


class WindowDetector:
    """
    窗口检测器

    用法:
        detector = WindowDetector()
        windows = detector.find_by_title("记事本")
        # windows: [WindowInfo, ...]
    """

    def __init__(self):
        if not HAS_WIN32:
            raise RuntimeError("窗口检测需要安装 pywin32")

    def find_by_title(self, title: str, exact: bool = False) -> list[WindowInfo]:
        """
        按窗口标题查找

        Args:
            title: 窗口标题（或其一部分）
            exact: True 精确匹配，False 包含匹配

        Returns:
            匹配的 WindowInfo 列表
        """
        results = []

        def callback(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            win_title = win32gui.GetWindowText(hwnd)
            if exact:
                match = (win_title == title)
            else:
                match = title.lower() in win_title.lower()
            if match:
                results.append(self._get_window_info(hwnd))

        win32gui.EnumWindows(callback, None)
        return results

    def find_by_class(self, class_name: str) -> list[WindowInfo]:
        """
        按窗口类名精确匹配

        Args:
            class_name: 窗口类名

        Returns:
            匹配的 WindowInfo 列表
        """
        results = []

        def callback(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            win_class = win32gui.GetClassName(hwnd)
            if win_class == class_name:
                results.append(self._get_window_info(hwnd))

        win32gui.EnumWindows(callback, None)
        return results

    def find_by_pid(self, pid: int) -> list[WindowInfo]:
        """
        按进程 ID 查找

        Args:
            pid: 进程 ID

        Returns:
            匹配的 WindowInfo 列表
        """
        results = []

        def callback(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid:
                results.append(self._get_window_info(hwnd))

        win32gui.EnumWindows(callback, None)
        return results

    def find_one(self, title: str) -> WindowInfo | None:
        """查找第一个匹配标题的窗口"""
        windows = self.find_by_title(title)
        return windows[0] if windows else None

    def list_all_visible(self) -> list[WindowInfo]:
        """列出所有可见窗口"""
        results = []

        def callback(hwnd, _extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # 过滤无标题窗口
                    results.append(self._get_window_info(hwnd))

        win32gui.EnumWindows(callback, None)
        return results

    @staticmethod
    def get_by_hwnd(hwnd: int) -> WindowInfo | None:
        """通过句柄获取窗口信息"""
        if not HAS_WIN32:
            return None
        try:
            return WindowDetector._get_window_info(hwnd)
        except Exception:
            return None

    @staticmethod
    def _get_window_info(hwnd: int) -> WindowInfo:
        """获取单个窗口的完整信息"""
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        is_visible = win32gui.IsWindowVisible(hwnd)
        placement = win32gui.GetWindowPlacement(hwnd)
        is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED

        return WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            rect=rect,
            pid=pid,
            is_visible=is_visible,
            is_minimized=is_minimized,
        )
