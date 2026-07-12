"""键盘操作模块 — 单键、组合键、长按

依赖 pyautogui 作为默认后端，支持 dry_run 模式。
所有操作前加入 5~15ms 随机延迟，模拟人类输入节奏。
"""

import time
import random
from dataclasses import dataclass
from typing import Optional

try:
    import pyautogui as _pyautogui
except ImportError:
    _pyautogui = None


# ═══════════════════════════════════════════
# 异常
# ═══════════════════════════════════════════

class KeyboardException(Exception):
    """键盘操作异常"""
    def __init__(self, message: str, key: str = "", operation: str = ""):
        super().__init__(message)
        self.key = key
        self.operation = operation


# ═══════════════════════════════════════════
# 操作结果
# ═══════════════════════════════════════════

@dataclass
class OpResult:
    """操作结果"""
    success: bool
    duration_ms: float       # 实际耗时（毫秒）
    error: Optional[str] = None
    detail: Optional[str] = None   # 附加信息（如按键名、坐标等）

    def __bool__(self) -> bool:
        return self.success


# ═══════════════════════════════════════════
# 按键映射
# ═══════════════════════════════════════════

class KeyMap:
    """特殊键映射表 — 支持中英文别名"""

    # 修饰键
    MODIFIERS = {"alt", "ctrl", "shift", "win", "cmd", "command"}

    # 特殊键别名：中文/简写 → pyautogui 标准名
    ALIAS: dict[str, str] = {
        # 回车
        "enter": "enter", "回车": "enter", "确认": "enter", "return": "enter",
        # 空格
        "space": "space", "空格": "space", " ": "space",
        # 退格
        "backspace": "backspace", "退格": "backspace", "删除": "backspace",
        # Tab
        "tab": "tab", "制表": "tab",
        # Esc
        "esc": "esc", "escape": "esc", "取消": "esc",
        # 方向键
        "up": "up", "上": "up",
        "down": "down", "下": "down",
        "left": "left", "左": "left",
        "right": "right", "右": "right",
        # 功能键
        "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
        "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
        "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
        # 导航
        "home": "home", "行首": "home",
        "end": "end", "行尾": "end",
        "pageup": "pageup", "上页": "pageup", "pgup": "pageup",
        "pagedown": "pagedown", "下页": "pagedown", "pgdn": "pagedown",
        # 编辑
        "insert": "insert", "插入": "insert",
        "delete": "delete", "del": "delete",
        "printscreen": "printscreen", "prtsc": "printscreen", "截屏": "printscreen",
        "scrolllock": "scrolllock",
        "pause": "pause",
        # 修饰键
        "alt": "alt", "altleft": "altleft", "altright": "altright",
        "ctrl": "ctrl", "control": "ctrl", "ctrlleft": "ctrlleft", "ctrlright": "ctrlright",
        "shift": "shift", "shiftleft": "shiftleft", "shiftright": "shiftright",
        "win": "win", "windows": "win", "cmd": "win", "command": "win",
        "winleft": "winleft", "winright": "winright",
        # 数字键盘
        "num0": "num0", "num1": "num1", "num2": "num2", "num3": "num3", "num4": "num4",
        "num5": "num5", "num6": "num6", "num7": "num7", "num8": "num8", "num9": "num9",
        "numlock": "numlock",
        "numadd": "numadd", "numsub": "numsubtract", "nummult": "nummultiply", "numdiv": "numdivide",
        # 符号
        "capslock": "capslock", "大写": "capslock",
        "volumemute": "volumemute", "静音": "volumemute",
        "volumeup": "volumeup", "音量加": "volumeup",
        "volumedown": "volumedown", "音量减": "volumedown",
    }

    @classmethod
    def normalize(cls, key: str) -> str:
        """将别名转为 pyautogui 标准键名，未知键原样返回"""
        k = key.strip().lower()
        return cls.ALIAS.get(k, key)

    @classmethod
    def is_modifier(cls, key: str) -> bool:
        """判断是否为修饰键"""
        return cls.normalize(key) in cls.MODIFIERS


# ═══════════════════════════════════════════
# 键盘控制器
# ═══════════════════════════════════════════

class KeyboardController:
    """键盘操作控制器

    参数:
        dry_run: True 时不实际操作，仅记录日志
        min_delay_ms / max_delay_ms: 操作前随机延迟范围（毫秒）
    """

    def __init__(
        self,
        dry_run: bool = False,
        min_delay_ms: int = 5,
        max_delay_ms: int = 15,
    ):
        self.dry_run = dry_run
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    # ── 内部 ────────────────────────────

    def _check_available(self):
        """检查 pyautogui 是否可用"""
        if _pyautogui is None:
            raise KeyboardException(
                "pyautogui 未安装，无法执行键盘操作。请运行: pip install pyautogui",
                operation="check",
            )

    def _random_delay(self):
        """操作前随机微小延迟（5~15ms），模拟人类节奏"""
        if not self.dry_run:
            ms = random.randint(self.min_delay_ms, self.max_delay_ms)
            time.sleep(ms / 1000.0)

    def _normalize_key(self, key: str) -> str:
        """规范化按键名"""
        return KeyMap.normalize(key)

    # ── 公开接口 ─────────────────────────

    def key_press(self, key: str) -> OpResult:
        """单键按下+释放

        参数:
            key: 按键名，支持中英文别名（如 "回车"、"a"、"space"）

        返回:
            OpResult(success=True/False, duration_ms=...)

        示例:
            controller.key_press("a")
            controller.key_press("回车")
        """
        start = time.perf_counter()
        key = self._normalize_key(key)

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"dry_run: press '{key}'")

        try:
            self._check_available()
            self._random_delay()
            _pyautogui.press(key)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"press '{key}'")
        except KeyboardException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=False, duration_ms=elapsed, error=str(e), detail=f"press '{key}'")

    def key_combo(self, keys: list[str]) -> OpResult:
        """组合键 — 同时按下多个键

        修饰键（ctrl/alt/shift/win）需放在列表中，
        方法会自动调用 pyautogui.hotkey()。

        参数:
            keys: 按键列表，如 ["ctrl", "c"]、["alt", "tab"]

        返回:
            OpResult

        示例:
            controller.key_combo(["ctrl", "c"])    # 复制
            controller.key_combo(["ctrl", "a"])    # 全选
            controller.key_combo(["alt", "f4"])    # 关闭窗口
        """
        start = time.perf_counter()
        if not keys:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=False, duration_ms=elapsed, error="按键列表为空")

        normalized = [self._normalize_key(k) for k in keys]
        combo_str = "+".join(normalized)

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"dry_run: combo '{combo_str}'")

        try:
            self._check_available()
            self._random_delay()
            # pyautogui.hotkey 接收可变参数
            _pyautogui.hotkey(*normalized)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"combo '{combo_str}'")
        except KeyboardException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=False, duration_ms=elapsed, error=str(e), detail=f"combo '{combo_str}'")

    def key_hold(self, key: str, duration_ms: float) -> OpResult:
        """长按指定时长后释放

        参数:
            key: 按键名
            duration_ms: 按住时长（毫秒），最小 10ms

        返回:
            OpResult

        示例:
            controller.key_hold("w", 2000)   # 按住 W 键 2 秒
            controller.key_hold("shift", 500) # 按住 Shift 0.5 秒
        """
        start = time.perf_counter()
        key = self._normalize_key(key)
        duration_ms = max(duration_ms, 10)  # 最小时长保护

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"dry_run: hold '{key}' {duration_ms:.0f}ms",
            )

        try:
            self._check_available()
            self._random_delay()
            _pyautogui.keyDown(key)
            time.sleep(duration_ms / 1000.0)
            _pyautogui.keyUp(key)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=True, duration_ms=elapsed,
                detail=f"hold '{key}' {duration_ms:.0f}ms",
            )
        except KeyboardException:
            raise
        except Exception as e:
            # 确保释放按键
            try:
                _pyautogui.keyUp(key)
            except Exception:
                pass
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(
                success=False, duration_ms=elapsed, error=str(e),
                detail=f"hold '{key}' {duration_ms:.0f}ms",
            )

    def type_text(self, text: str, interval_ms: float = 0) -> OpResult:
        """逐字输入文本（模拟键盘打字）

        参数:
            text: 要输入的文本
            interval_ms: 每个字符之间的间隔（毫秒），0 表示使用 pyautogui 默认速度

        返回:
            OpResult
        """
        start = time.perf_counter()

        if self.dry_run:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"dry_run: type '{text[:20]}...'")

        try:
            self._check_available()
            self._random_delay()
            if interval_ms > 0:
                _pyautogui.typewrite(text, interval=interval_ms / 1000.0)
            else:
                _pyautogui.typewrite(text)
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=True, duration_ms=elapsed, detail=f"type {len(text)} chars")
        except KeyboardException:
            raise
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return OpResult(success=False, duration_ms=elapsed, error=str(e))
