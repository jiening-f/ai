"""窗口操作 — 置顶、移动、最小化、恢复等"""
import time
from typing import Optional, Dict, Any

from core.constants import _flog

# ── Win32 依赖 ────────────────────────────────
try:
    import win32gui
    import win32con
    import win32api
    import win32process
    _HAS_W32 = True
except ImportError:
    _HAS_W32 = False


# ══ 私有 Win32 封装 ════════════════════════════════

def _win32_is_window(hwnd: int) -> bool:
    """检查窗口句柄是否仍然有效"""
    try:
        return win32gui.IsWindow(hwnd)
    except Exception:
        return False


def _win32_get_window_rect(hwnd: int) -> Optional[tuple]:
    """获取窗口矩形 (x, y, w, h)"""
    try:
        x1, y1, x2, y2 = win32gui.GetWindowRect(hwnd)
        return (x1, y1, x2 - x1, y2 - y1)
    except Exception:
        return None


def _win32_get_window_text(hwnd: int) -> str:
    """获取窗口标题"""
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


def _win32_get_class_name(hwnd: int) -> str:
    """获取窗口类名"""
    try:
        return win32gui.GetClassName(hwnd)
    except Exception:
        return ""


def _win32_is_minimized(hwnd: int) -> bool:
    """检查窗口是否已最小化"""
    try:
        return win32gui.IsIconic(hwnd)
    except Exception:
        return False


def _win32_get_placement(hwnd: int) -> Optional[int]:
    """获取窗口显示状态（SW_SHOWNORMAL / SW_SHOWMINIMIZED 等）"""
    try:
        import ctypes
        from ctypes import wintypes

        class WINDOWPLACEMENT(ctypes.Structure):
            _fields_ = [
                ("length", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("showCmd", wintypes.DWORD),
            ]

        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(WINDOWPLACEMENT)
        ctypes.windll.user32.GetWindowPlacement(
            ctypes.c_void_p(hwnd), ctypes.byref(wp)
        )
        return wp.showCmd
    except Exception:
        return None


# ══ 窗口操作器 ═════════════════════════════════════

class WindowOperator:
    """窗口操作

    提供窗口的置顶激活、移动、调整大小、最小化、恢复等操作，
    所有 Win32 调用封装在 _win32_* 私有方法中。
    """

    @staticmethod
    def get_window_info(hwnd: int) -> Optional[Dict[str, Any]]:
        """获取窗口详细信息
        Args:
            hwnd: 窗口句柄
        Returns:
            包含 x/y/width/height/title/classname/is_minimized 的字典
        """
        if not _HAS_W32:
            _flog("窗口操作: pywin32 未安装")
            return None

        if not _win32_is_window(hwnd):
            _flog(f"窗口操作: 句柄 {hwnd} 已失效")
            return None

        rect = _win32_get_window_rect(hwnd)
        if not rect:
            return None

        title = _win32_get_window_text(hwnd)
        classname = _win32_get_class_name(hwnd)
        minimized = _win32_is_minimized(hwnd)

        return {
            "hwnd": hwnd,
            "title": title,
            "classname": classname,
            "x": rect[0],
            "y": rect[1],
            "width": rect[2],
            "height": rect[3],
            "is_minimized": minimized,
        }

    @staticmethod
    def set_foreground(hwnd: int) -> bool:
        """将窗口置顶并激活
        使用多种策略确保窗口真正获得焦点：
        1. AttachThreadInput 线程附加
        2. Alt 键模拟（绕过前台锁定）
        3. 直接 SetForegroundWindow
        Args:
            hwnd: 窗口句柄
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        try:
            if not _win32_is_window(hwnd):
                _flog("窗口操作: 句柄失效，无法置顶")
                return False

            # 如果已最小化，先恢复
            if _win32_is_minimized(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)

            # 策略1: AttachThreadInput
            try:
                cur_tid = win32api.GetCurrentThreadId()
                _, target_tid = win32process.GetWindowThreadProcessId(hwnd)
                win32process.AttachThreadInput(cur_tid, target_tid, True)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.1)
                win32process.AttachThreadInput(cur_tid, target_tid, False)
                return True
            except Exception:
                pass

            # 策略2: Alt 键模拟
            try:
                win32api.keybd_event(0x12, 0, 0, 0)  # Alt 按下
                time.sleep(0.02)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.02)
                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt 抬起
                return True
            except Exception:
                pass

            # 策略3: 直接调用
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            return True
        except Exception as e:
            _flog(f"窗口置顶异常: {e}")
            return False

    @staticmethod
    def move_window(hwnd: int, x: int, y: int, w: int, h: int) -> bool:
        """移动并调整窗口大小
        Args:
            hwnd: 窗口句柄
            x, y: 新位置（左上角坐标）
            w, h: 新大小（宽度、高度）
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        try:
            if not _win32_is_window(hwnd):
                _flog(f"窗口操作: 句柄 {hwnd} 已失效")
                return False

            # 如果最小化，先恢复
            if _win32_is_minimized(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)

            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            return True
        except Exception as e:
            _flog(f"窗口移动异常: {e}")
            return False

    @staticmethod
    def minimize(hwnd: int) -> bool:
        """最小化窗口
        Args:
            hwnd: 窗口句柄
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        try:
            if not _win32_is_window(hwnd):
                _flog(f"窗口操作: 句柄 {hwnd} 已失效")
                return False
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            _flog(f"窗口最小化异常: {e}")
            return False

    @staticmethod
    def restore(hwnd: int) -> bool:
        """恢复已最小化的窗口
        Args:
            hwnd: 窗口句柄
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        try:
            if not _win32_is_window(hwnd):
                _flog(f"窗口操作: 句柄 {hwnd} 已失效")
                return False
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception as e:
            _flog(f"窗口恢复异常: {e}")
            return False

    @staticmethod
    def is_window_alive(hwnd: int) -> bool:
        """检查窗口是否仍然存在且有效
        Args:
            hwnd: 窗口句柄
        Returns:
            窗口是否存活
        """
        if not _HAS_W32 or not hwnd:
            return False
        return _win32_is_window(hwnd)

    @staticmethod
    def resize(hwnd: int, w: int, h: int) -> bool:
        """调整窗口大小（保持当前位置）
        Args:
            hwnd: 窗口句柄
            w, h: 新宽度、新高度
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        rect = _win32_get_window_rect(hwnd)
        if not rect:
            return False

        return WindowOperator.move_window(hwnd, rect[0], rect[1], w, h)

    @staticmethod
    def move(hwnd: int, x: int, y: int) -> bool:
        """移动窗口（保持当前大小）
        Args:
            hwnd: 窗口句柄
            x, y: 新位置
        Returns:
            是否成功
        """
        if not _HAS_W32 or not hwnd:
            return False

        rect = _win32_get_window_rect(hwnd)
        if not rect:
            return False

        return WindowOperator.move_window(hwnd, x, y, rect[2], rect[3])


# ── 便捷函数 ────────────────────────────────────
get_window_info = WindowOperator.get_window_info
set_foreground = WindowOperator.set_foreground
move_window = WindowOperator.move_window
move = WindowOperator.move
resize = WindowOperator.resize
minimize = WindowOperator.minimize
restore = WindowOperator.restore
is_window_alive = WindowOperator.is_window_alive
