"""窗口检测与查找 — 按标题/类名/进程名匹配"""
from typing import Optional, List, Dict, Any

from core.constants import _flog

# ── Win32 依赖 ────────────────────────────────
try:
    import win32gui
    import win32process
    import psutil
    _HAS_W32 = True
except ImportError:
    _HAS_W32 = False


def is_available() -> bool:
    """检查窗口检测模块是否可用（pywin32 + psutil 是否已安装）"""
    return _HAS_W32


# ══ 私有 Win32 封装 ════════════════════════════════

def _win32_get_process_name(pid: int) -> str:
    """通过 PID 获取进程名"""
    try:
        proc = psutil.Process(pid)
        return proc.name()
    except Exception:
        pass
    return ""


def _win32_get_pid(hwnd: int) -> int:
    """获取窗口所属进程 PID"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return 0


def _win32_enum_windows(only_visible: bool = True) -> List[int]:
    """枚举所有顶层窗口句柄"""
    results = []

    def _callback(hwnd, _ctx):
        if only_visible and not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        results.append(hwnd)
        return True

    win32gui.EnumWindows(_callback, None)
    return results


def _win32_get_window_detail(hwnd: int) -> Optional[Dict[str, Any]]:
    """获取单个窗口的详细信息"""
    try:
        if not win32gui.IsWindow(hwnd):
            return None
        title = win32gui.GetWindowText(hwnd)
        classname = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        x, y, r, b = rect
        w, h = r - x, b - y
        visible = win32gui.IsWindowVisible(hwnd)
        pid = _win32_get_pid(hwnd)
        process_name = _win32_get_process_name(pid)
        return {
            "hwnd": hwnd,
            "title": title,
            "classname": classname,
            "rect": (x, y, w, h),
            "x": x, "y": y, "width": w, "height": h,
            "pid": pid,
            "process_name": process_name,
            "visible": visible,
        }
    except Exception:
        return None


# ══ 窗口检测器 ═════════════════════════════════════

class WindowDetector:
    """窗口检测与查找

    支持按标题、类名、进程名三种方式匹配窗口，
    所有 Win32 调用封装在 _win32_* 私有方法中。
    """

    @staticmethod
    def find_by_title(title: str, exact: bool = False) -> List[Dict[str, Any]]:
        """按窗口标题查找（默认模糊匹配，含有关键词即可）
        Args:
            title: 窗口标题关键词
            exact: True 精确匹配，False 模糊匹配（默认）
        Returns:
            匹配的窗口信息列表，每项含 hwnd/title/classname/rect/pid/process_name
        """
        if not _HAS_W32:
            _flog("窗口检测: pywin32 未安装")
            return []

        results = []
        keyword = title.lower()

        for hwnd in _win32_enum_windows(only_visible=True):
            detail = _win32_get_window_detail(hwnd)
            if not detail:
                continue
            win_title = detail["title"]
            if exact:
                if win_title == title:
                    results.append(detail)
            else:
                if keyword in win_title.lower():
                    results.append(detail)

        return results

    @staticmethod
    def find_by_classname(classname: str) -> List[Dict[str, Any]]:
        """按窗口类名精确匹配
        Args:
            classname: 窗口类名（如 "Notepad"、"UnityWndClass"）
        Returns:
            匹配的窗口信息列表
        """
        if not _HAS_W32:
            _flog("窗口检测: pywin32 未安装")
            return []

        results = []
        target = classname.lower()

        for hwnd in _win32_enum_windows(only_visible=True):
            detail = _win32_get_window_detail(hwnd)
            if not detail:
                continue
            if detail["classname"].lower() == target:
                results.append(detail)

        return results

    @staticmethod
    def find_by_process(process_name: str) -> List[Dict[str, Any]]:
        """按进程名匹配窗口（模糊匹配，含有关键词即可）
        Args:
            process_name: 进程名关键词（如 "notepad.exe"、"game.exe"）
        Returns:
            匹配的窗口信息列表
        """
        if not _HAS_W32:
            _flog("窗口检测: pywin32 未安装")
            return []

        results = []
        keyword = process_name.lower()

        for hwnd in _win32_enum_windows(only_visible=True):
            detail = _win32_get_window_detail(hwnd)
            if not detail:
                continue
            pname = detail["process_name"].lower()
            if keyword in pname:
                results.append(detail)

        return results

    @staticmethod
    def find(
        title: Optional[str] = None,
        classname: Optional[str] = None,
        process_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """组合条件查找窗口，返回同时满足所有条件的窗口列表
        Args:
            title: 窗口标题关键词（可选）
            classname: 窗口类名（可选）
            process_name: 进程名关键词（可选）
        Returns:
            同时满足所有条件的窗口信息列表
        """
        if not _HAS_W32:
            _flog("窗口检测: pywin32 未安装")
            return []

        title_kw = title.lower() if title else None
        classname_kw = classname.lower() if classname else None
        proc_kw = process_name.lower() if process_name else None

        results = []
        for hwnd in _win32_enum_windows(only_visible=True):
            detail = _win32_get_window_detail(hwnd)
            if not detail:
                continue

            if title_kw and title_kw not in detail["title"].lower():
                continue
            if classname_kw and detail["classname"].lower() != classname_kw:
                continue
            if proc_kw and proc_kw not in detail["process_name"].lower():
                continue

            results.append(detail)

        return results

    @staticmethod
    def enum_visible(min_width: int = 100, min_height: int = 100) -> List[Dict[str, Any]]:
        """枚举所有可见的顶层窗口
        Args:
            min_width: 最小窗口宽度（过滤小窗口，默认 100px）
            min_height: 最小窗口高度（默认 100px）
        Returns:
            可见窗口列表，按进程名排序
        """
        if not _HAS_W32:
            _flog("窗口检测: pywin32 未安装")
            return []

        results = []
        for hwnd in _win32_enum_windows(only_visible=True):
            detail = _win32_get_window_detail(hwnd)
            if not detail:
                continue
            w, h = detail["width"], detail["height"]
            if w >= min_width and h >= min_height:
                results.append(detail)

        # 按进程名排序
        results.sort(key=lambda d: d["process_name"].lower())
        return results


# ── 便捷函数 ────────────────────────────────────
find_by_title = WindowDetector.find_by_title
find_by_classname = WindowDetector.find_by_classname
find_by_process = WindowDetector.find_by_process
find_all = WindowDetector.find
enum_visible = WindowDetector.enum_visible
