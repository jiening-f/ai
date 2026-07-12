"""
键盘输入模拟服务

支持：
- 单键按下/释放
- 组合键（修饰键 + 普通键）
- 长按
- 随机微延迟（模拟人类操作）
- dry_run 模式（不实际操作）
"""

import time
import random

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


# 特殊键映射：逻辑名称 → pyautogui 键名
KEY_MAP = {
    "enter": "enter",
    "tab": "tab",
    "esc": "esc",
    "escape": "esc",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
    "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
    "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
    "alt": "alt",
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "win": "win",
    "windows": "win",
    "cmd": "win",
    "printscreen": "printscreen",
    "capslock": "capslock",
    "numlock": "numlock",
    "scrolllock": "scrolllock",
}


class KeyboardService:
    """
    键盘输入模拟服务

    用法:
        kb = KeyboardService()
        kb.key_press("a")
        kb.key_combo(["ctrl", "c"])
        kb.key_hold("a", 500)
    """

    def __init__(self, dry_run: bool = False, min_delay_ms: int = 5, max_delay_ms: int = 15):
        self.dry_run = dry_run
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    def key_press(self, key: str):
        """
        按下并释放一个键

        Args:
            key: 按键名称（单字符或 KEY_MAP 中的键名）
        """
        self._random_delay()

        if self.dry_run:
            return

        mapped = self._map_key(key)
        if HAS_PYAUTOGUI:
            pyautogui.press(mapped)
        self._random_delay()

    def key_combo(self, keys: list[str]):
        """
        组合键（如 Ctrl+C）

        Args:
            keys: 按键列表，第一个通常是修饰键，如 ["ctrl", "c"]
        """
        self._random_delay()

        if self.dry_run:
            return

        mapped = [self._map_key(k) for k in keys]
        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*mapped)
        self._random_delay()

    def key_hold(self, key: str, duration_ms: int = 500):
        """
        长按指定时长

        Args:
            key: 按键名称
            duration_ms: 按住毫秒数
        """
        self._random_delay()

        if self.dry_run:
            return

        mapped = self._map_key(key)
        if HAS_PYAUTOGUI:
            pyautogui.keyDown(mapped)
            time.sleep(duration_ms / 1000.0)
            pyautogui.keyUp(mapped)
        self._random_delay()

    def key_down(self, key: str):
        """按下键（不释放），需配合 key_up 使用"""
        mapped = self._map_key(key)
        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.keyDown(mapped)

    def key_up(self, key: str):
        """释放键"""
        mapped = self._map_key(key)
        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.keyUp(mapped)

    def type_text(self, text: str, interval_ms: float = 0):
        """
        逐字输入文本

        Args:
            text: 要输入的文本
            interval_ms: 字符间间隔（秒）
        """
        if not self.dry_run and HAS_PYAUTOGUI:
            pyautogui.typewrite(text, interval=interval_ms)

    @staticmethod
    def _map_key(key: str) -> str:
        """将逻辑键名映射到 pyautogui 键名"""
        lower = key.lower().strip()
        return KEY_MAP.get(lower, lower)

    def _random_delay(self):
        """随机微延迟（模拟人类操作间隔）"""
        delay = random.uniform(self.min_delay_ms, self.max_delay_ms) / 1000.0
        time.sleep(delay)
