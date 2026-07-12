"""鼠标操作模块 — 点击、拖拽、滚轮、贝塞尔曲线移动

依赖 pyautogui 作为默认后端，支持 dry_run 模式。
支持三种移动速度：instant（瞬移）、linear（匀速）、human_like（贝塞尔曲线）。
"""

import time
import random
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Literal

try:
    import pyautogui as _pyautogui
except ImportError:
    _pyautogui = None


# ═══════════════════════════════════════════
# 枚举 & 常量
# ═══════════════════════════════════════════

class MoveSpeed(Enum):
    """鼠标移动速度模式"""
    INSTANT = "instant"       # 瞬移 — 不经过中间点
    LINEAR = "linear"         # 匀速 — 固定步数线性移动
    HUMAN_LIKE = "human_like" # 人类模拟 — 贝塞尔曲线 + 终点偏移


class MouseException(Exception):
    """鼠标操作异常"""
    def __init__(self, message: str, position: tuple = (), operation: str = ""):
        super().__init__(message)
        self.position = position
        self.operation = operation


@dataclass
class Position:
    """坐标点"""
    x: int
    y: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    @staticmethod
    def from_tuple(t: tuple[int, int]) -> "Position":
        return Position(t[0], t[1])


# 从 keyboard 导入 OpResult（避免循环引用，这里重定义一个精简版）
@dataclass
class OpResult:
    """操作结果"""
    success: bool
    duration_ms: float
    error: Optional[str] = None
    detail: Optional[str] = None

    def __bool__(self) -> bool:
        return self.success


# ═══════════════════════════════════════════
# 贝塞尔曲线
# ═══════════════════════════════════════════

class BezierPath:
    """三次贝塞尔曲线路径计算器

    控制点自动生成：P0=起点, P1/P2=随机偏移控制点, P3=终点
    """

    @staticmethod
    def _cubic_bezier(t: float, p0: tuple, p1: tuple, p2: tuple, p3: tuple) -> tuple[float, float]:
        """三次贝塞尔曲线：B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3"""
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        return (x, y)

    @classmethod
    def generate(
        cls,
        start: tuple[int, int],
        end: tuple[int, int],
        num_points: int = 30,
        curvature: float = 0.2,
    ) -> list[tuple[int, int]]:
        """生成从起点到终点的贝塞尔曲线路径点

        参数:
            start: 起点坐标
            end: 终点坐标
            num_points: 路径点数量（越多越平滑）
            curvature: 曲率 0~1，越大曲线越弯。默认 0.2 为微弧

        返回:
            路径点列表 [(x, y), ...]
        """
        sx, sy = start
        ex, ey = end
        dist = math.hypot(ex - sx, ey - sy)

        if dist < 5:
            return [end]

        # 控制点偏移量随距离缩放
        offset = dist * curvature

        # P1: 起点附近，偏向终点方向 + 随机扰动
        p1x = sx + (ex - sx) * 0.25 + random.uniform(-offset, offset)
        p1y = sy + (ey - sy) * 0.25 + random.uniform(-offset, offset)

        # P2: 终点附近，偏向起点方向 + 随机扰动
        p2x = ex - (ex - sx) * 0.25 + random.uniform(-offset, offset)
        p2y = ey - (ey - sy) * 0.25 + random.uniform(-offset, offset)

        points: list[tuple[int, int]] = []
        for i in range(num_points + 1):
            t = i / num_points
            px, py = cls._cubic_bezier(t, start, (p1x, p1y), (p2x, p2y), end)
            points.append((int(px), int(py)))

        return points


# ═══════════════════════════════════════════
# 鼠标控制器
# ═══════════════════════════════════════════

class MouseController:
    """鼠标操作控制器

    参数:
        dry_run: True 时不实际操作
        speed: 移动速度模式 (instant / linear / human_like)
        min_delay_ms / max_delay_ms: 操作前随机延迟范围
        endpoint_jitter: 人类模拟时终点 ±N px 的随机偏移
    """

    def __init__(
        self,
        dry_run: bool = False,
        speed: MoveSpeed = MoveSpeed.HUMAN_LIKE,
        min_delay_ms: int = 5,
        max_delay_ms: int = 15,
        endpoint_jitter: int = 2,
    ):
        self.dry_run = dry_run
        self.speed = speed
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.endpoint_jitter = endpoint_jitter

    # ── 内部 ────────────────────────────

    def _check_available(self):
        """检查 pyautogui 是否可用"""
        if _pyautogui is None:
            raise MouseException(
                "pyautogui 未安装，无法执行鼠标操作。请运行: pip install pyautogui",
                operation="check",
            )

    def _random_delay(self):
        """操作前随机微小延迟"""
        if not self.dry_run:
            ms = random.randint(self.min_delay_ms, self.max_delay_ms)
            time.sleep(ms / 1000.0)

    def _resolve_position(self, x: int, y: int, relative: bool = False) -> tuple[int, int]:
        """解析坐标：支持绝对坐标和相对坐标"""
        if relative:
            if _pyautogui is None:
                raise MouseException("pyautogui 未安装", operation="resolve")
            cx, cy = _pyautogui.position()
            return (cx + x, cy + y)
        return (x, y)

    def _move_to(
        self, x: int, y: int, speed: Optional[MoveSpeed] = None
    ) -> tuple[int, int]:
        """根据速度模式移动到目标位置，返回实际到达的坐标"""
        sp = speed or self.speed

        if sp == MoveSpeed.INSTANT:
            actual_x, actual_y = x, y
            _pyautogui.moveTo(actual_x, actual_y, duration=0.0)

        elif sp == MoveSpeed.LINEAR:
            # 匀速移动，时长与距离成正比
            cx, cy = _pyautogui.position()
            dist = math.hypot(x - cx, y - cy)
            duration = min(dist / 1000.0, 0.3)  # 最大 300ms
            _pyautogui.moveTo(x, y, duration=max(duration, 0.02))
            actual_x, actual_y = x, y

        else:  # HUMAN_LIKE
            # 终点微小随机偏移（±2px）
            jx = random.randint(-self.endpoint_jitter, self.endpoint_jitter)
            jy = random.randint(-self.endpoint_jitter, self.endpoint_jitter)
            target_x, target_y = x + jx, y + jy

            cx, cy = _pyautogui.position()
            dist = math.hypot(target_x - cx, target_y - cy)

            if dist < 3:
                actual_x, actual_y = target_x, target_y
            elif dist < 30:
                # 短距离：线性移动
                _pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.03, 0.08))
                actual_x, actual_y = target_x, target_y
            else:
                # 长距离：贝塞尔曲线
                path = BezierPath.generate(
                    (cx, cy), (target_x, target_y),
                    num_points=max(int(dist / 15), 8),
                    curvature=random.uniform(0.1, 0.3),
                )
                step_duration = random.uniform(0.002, 0.005)
                for px, py in path:
                    _pyautogui.moveTo(px, py, duration=step_duration)
                actual_x, actual_y = target_x, target_y

        return (actual_x, actual_y)

    # ── 公开接口 ─────────────────────────

    def mouse_click(
        self, x: int, y: int, *, button: str = "left", relative: bool = False
    ) -> OpResult:
        """鼠标单击

        参数:
            x, y: 目标坐标
            button: 按键 — "left" / "right" / "middle"
            relative: True 时为相对于当前位置的偏移坐标

        返回:
            OpResult

        示例:
            mouse.mouse_click(100, 200)
            mouse.mouse_click(50, 0, relative=True)       # 从当前位置右移 50px
            mouse.mouse_click(200, 300, button="right")    # 右键单击
        """
        start = time.perf_counter()
        tx, ty = self._resolve_position(x, y, relative)

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dry_run: click {button} at ({tx},{ty})",
            )

        try:
            self._check_available()
            self._random_delay()
            ax, ay = self._move_to(tx, ty)
            # pyautogui.click 的 button 参数
            if button == "right":
                _pyautogui.rightClick(ax, ay)
            elif button == "middle":
                _pyautogui.middleClick(ax, ay)
            else:
                _pyautogui.click(ax, ay)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"click {button} at ({ax},{ay})",
            )
        except MouseException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=False, duration_ms=elapsed, error=str(e),
                detail=f"click {button} at ({tx},{ty})",
            )

    def mouse_dblclick(self, x: int, y: int, *, relative: bool = False) -> OpResult:
        """鼠标左键双击

        参数:
            x, y: 目标坐标
            relative: True 时为相对坐标

        返回:
            OpResult
        """
        start = time.perf_counter()
        tx, ty = self._resolve_position(x, y, relative)

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dry_run: dblclick at ({tx},{ty})",
            )

        try:
            self._check_available()
            self._random_delay()
            ax, ay = self._move_to(tx, ty)
            _pyautogui.doubleClick(ax, ay)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dblclick at ({ax},{ay})",
            )
        except MouseException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=False, duration_ms=elapsed, error=str(e),
                detail=f"dblclick at ({tx},{ty})",
            )

    def mouse_right(self, x: int, y: int, *, relative: bool = False) -> OpResult:
        """鼠标右键单击 — mouse_click(x, y, button="right") 的快捷方式"""
        return self.mouse_click(x, y, button="right", relative=relative)

    def mouse_drag(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration_ms: float = 500,
        *,
        relative: bool = False,
    ) -> OpResult:
        """鼠标拖拽 — 从 (x1,y1) 拖动到 (x2,y2)

        参数:
            x1, y1: 起始坐标
            x2, y2: 终点坐标
            duration_ms: 拖拽时长（毫秒）
            relative: True 时为相对坐标

        返回:
            OpResult

        示例:
            mouse.mouse_drag(100, 100, 300, 300, duration_ms=800)
        """
        start = time.perf_counter()
        tx1, ty1 = self._resolve_position(x1, y1, relative)
        tx2, ty2 = self._resolve_position(x2, y2, relative)
        duration_sec = max(duration_ms / 1000.0, 0.05)

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dry_run: drag ({tx1},{ty1})→({tx2},{ty2}) {duration_ms:.0f}ms",
            )

        try:
            self._check_available()
            self._random_delay()
            # 先移动到起点
            self._move_to(tx1, ty1, speed=MoveSpeed.LINEAR)
            time.sleep(0.03)
            # 拖拽到终点
            _pyautogui.drag(
                tx2 - tx1, ty2 - ty1,
                duration=duration_sec,
                button="left",
            )
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"drag ({tx1},{ty1})→({tx2},{ty2}) {duration_ms:.0f}ms",
            )
        except MouseException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=False, duration_ms=elapsed, error=str(e),
                detail=f"drag ({tx1},{ty1})→({tx2},{ty2})",
            )

    def mouse_scroll(
        self, clicks: int, x: Optional[int] = None, y: Optional[int] = None
    ) -> OpResult:
        """滚轮滚动

        参数:
            clicks: 滚动格数，正=向上，负=向下
            x, y: 鼠标移动到的位置（可选，不传则在当前位置滚动）

        返回:
            OpResult

        示例:
            mouse.mouse_scroll(3)          # 向上滚 3 格
            mouse.mouse_scroll(-5)         # 向下滚 5 格
            mouse.mouse_scroll(2, 100, 200) # 移动到 (100,200) 再向上滚 2 格
        """
        start = time.perf_counter()

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            pos_str = f"at ({x},{y})" if x is not None else "current pos"
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dry_run: scroll {clicks} {pos_str}",
            )

        try:
            self._check_available()
            self._random_delay()
            if x is not None and y is not None:
                self._move_to(x, y, speed=MoveSpeed.LINEAR)
            _pyautogui.scroll(clicks)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"scroll {clicks}",
            )
        except MouseException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=False, duration_ms=elapsed, error=str(e),
                detail=f"scroll {clicks}",
            )

    def get_position(self) -> Position:
        """获取当前鼠标位置"""
        if _pyautogui is None:
            raise MouseException("pyautogui 未安装", operation="get_position")
        px, py = _pyautogui.position()
        return Position(px, py)
