"""
鼠标输入模拟服务

支持：
- 单击/双击/右键
- 拖拽
- 滚轮
- 移动模式：instant / linear / human_like
- 人类模拟：贝塞尔曲线移动 + 微小终点偏移
- dry_run 模式（不实际操作）
"""

import time
import random
import math

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class MouseService:
    """
    鼠标输入模拟服务

    用法:
        ms = MouseService()
        ms.mouse_click(100, 200)
        ms.mouse_drag(0, 0, 500, 500, duration_ms=1000)
    """

    def __init__(
        self,
        dry_run: bool = False,
        move_mode: str = "human_like",  # instant / linear / human_like
        default_duration_ms: int = 300,
        click_delay_ms: int = 50,
    ):
        self.dry_run = dry_run
        self.move_mode = move_mode
        self.default_duration_ms = default_duration_ms
        self.click_delay_ms = click_delay_ms

    def mouse_click(self, x: int, y: int, relative: bool = False):
        """
        左键单击

        Args:
            x, y: 坐标（绝对或相对）
            relative: True 表示相对于当前鼠标位置
        """
        if relative:
            cx, cy = self._current_pos()
            x, y = cx + x, cy + y

        self._move_to(x, y)
        time.sleep(self.click_delay_ms / 1000.0)

        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.click(x, y)

    def mouse_dblclick(self, x: int, y: int):
        """左键双击"""
        self._move_to(x, y)
        time.sleep(self.click_delay_ms / 1000.0)

        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.doubleClick(x, y)

    def mouse_right(self, x: int, y: int):
        """右键单击"""
        self._move_to(x, y)
        time.sleep(self.click_delay_ms / 1000.0)

        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.rightClick(x, y)

    def mouse_drag(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration_ms: int = 500,
    ):
        """
        拖拽：从 (x1, y1) 拖到 (x2, y2)

        Args:
            x1, y1: 起点
            x2, y2: 终点
            duration_ms: 拖拽时长
        """
        self._move_to(x1, y1)
        time.sleep(self.click_delay_ms / 1000.0)

        duration_sec = duration_ms / 1000.0

        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.mouseDown(x1, y1)
            self._move_to(x2, y2, duration_ms=duration_ms)
            time.sleep(0.05)
            pyautogui.mouseUp(x2, y2)

    def mouse_scroll(self, clicks: int, x: int = None, y: int = None):
        """
        滚轮滚动

        Args:
            clicks: 滚动格数（正=上，负=下）
            x, y: 可选，先移动到此处再滚动
        """
        if x is not None and y is not None:
            self._move_to(x, y)

        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.scroll(clicks, x=x, y=y)

    # ── 移动模式实现 ──────────────────

    def _move_to(self, x: int, y: int, duration_ms: int | None = None):
        """移动鼠标到目标位置"""
        if duration_ms is None:
            duration_ms = self.default_duration_ms

        if self.dry_run:
            return

        if self.move_mode == "instant":
            self._move_instant(x, y)
        elif self.move_mode == "linear":
            self._move_linear(x, y, duration_ms)
        elif self.move_mode == "human_like":
            self._move_human_like(x, y, duration_ms)

    @staticmethod
    def _move_instant(x: int, y: int):
        """瞬间移动"""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y, duration=0)

    @staticmethod
    def _move_linear(x: int, y: int, duration_ms: int):
        """匀速直线移动"""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y, duration=duration_ms / 1000.0)

    def _move_human_like(self, x: int, y: int, duration_ms: int):
        """
        人类模拟移动：贝塞尔曲线 + 微小终点偏移

        生成 2 个随机控制点的三次贝塞尔曲线，模拟手部自然移动轨迹。
        """
        if not HAS_PYAUTOGUI:
            return

        cx, cy = self._current_pos()
        # 微小终点偏移（模拟不精确点击）
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        tx, ty = x + offset_x, y + offset_y

        # 随机控制点（路径中点附近 ± 一定范围）
        mx = (cx + tx) / 2
        my = (cy + ty) / 2
        cp1x = mx + random.randint(-80, 80)
        cp1y = my + random.randint(-80, 80)
        cp2x = mx + random.randint(-50, 50)
        cp2y = my + random.randint(-50, 50)

        # 沿贝塞尔曲线采样
        steps = max(10, duration_ms // 10)
        step_delay = (duration_ms / 1000.0) / steps

        for i in range(1, steps + 1):
            t = i / steps
            # 三次贝塞尔: B(t) = (1-t)^3 P0 + 3(1-t)^2 t CP1 + 3(1-t) t^2 CP2 + t^3 P1
            px = ((1 - t) ** 3 * cx
                  + 3 * (1 - t) ** 2 * t * cp1x
                  + 3 * (1 - t) * t ** 2 * cp2x
                  + t ** 3 * tx)
            py = ((1 - t) ** 3 * cy
                  + 3 * (1 - t) ** 2 * t * cp1y
                  + 3 * (1 - t) * t ** 2 * cp2y
                  + t ** 3 * ty)
            pyautogui.moveTo(int(px), int(py), duration=0)
            time.sleep(step_delay)

    @staticmethod
    def _current_pos() -> tuple[int, int]:
        """获取当前鼠标位置"""
        if HAS_PYAUTOGUI:
            return pyautogui.position()
        return (0, 0)
