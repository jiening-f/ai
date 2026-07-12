"""窗口管理模块 — 窗口检测、操作、截图"""
from engine.window.detector import WindowDetector
from engine.window.operator import WindowOperator
from engine.window.capture import WindowCapture

# 便捷别名
win_find = WindowDetector.find_by_title
win_enum = WindowDetector.enum_visible
win_info = WindowOperator.get_window_info
win_top = WindowOperator.set_foreground
win_move = WindowOperator.move_window
win_min = WindowOperator.minimize
win_restore = WindowOperator.restore
win_alive = WindowOperator.is_window_alive
win_capture = WindowCapture.capture_window
