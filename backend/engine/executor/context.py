"""执行上下文 — 变量存储、截图缓存、运行状态、日志收集"""

from __future__ import annotations
from enum import Enum
from typing import Any


class RunState(Enum):
    """脚本运行状态"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class ExecutionContext:
    """脚本执行上下文

    贯穿整个脚本执行生命周期，提供：
    - 变量存取（支持嵌套键，如 "player.hp"）
    - 截图缓存（避免重复截图）
    - 运行状态控制
    - 日志收集（带时间戳）

    Usage:
        ctx = ExecutionContext()
        ctx.set_var("target", "开始游戏")
        ctx.cache_screenshot(img)
        ctx.log("检测到目标文字")
        if ctx.state == RunState.RUNNING:
            ...
    """

    def __init__(self):
        # ── 变量存储 ──
        self._vars: dict[str, Any] = {}

        # ── 截图缓存 ──
        self._screenshot_cache: Any = None  # numpy ndarray 或 None

        # ── 运行状态 ──
        self.state: RunState = RunState.STOPPED

        # ── 日志 ──
        self._logs: list[dict] = []

        # ── 扩展数据 ──
        self.extras: dict[str, Any] = {}

    # ── 变量操作 ──

    def set_var(self, key: str, value: Any) -> None:
        """设置变量值"""
        self._vars[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        """获取变量值，支持点号嵌套访问（如 "player.hp"）"""
        if "." in key:
            parts = key.split(".")
            current = self._vars
            for part in parts[:-1]:
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
            return current.get(parts[-1], default) if isinstance(current, dict) else default
        return self._vars.get(key, default)

    def get_all_vars(self) -> dict[str, Any]:
        """获取全部变量（只读副本）"""
        return dict(self._vars)

    def delete_var(self, key: str) -> bool:
        """删除变量，返回是否成功"""
        if key in self._vars:
            del self._vars[key]
            return True
        return False

    def clear_vars(self) -> None:
        """清空所有变量"""
        self._vars.clear()

    # ── 截图缓存 ──

    def cache_screenshot(self, image: Any) -> None:
        """缓存当前截图（numpy ndarray）"""
        self._screenshot_cache = image

    def get_screenshot(self) -> Any:
        """获取缓存的截图，可能为 None"""
        return self._screenshot_cache

    def clear_screenshot(self) -> None:
        """清除截图缓存"""
        self._screenshot_cache = None

    # ── 运行状态 ──

    @property
    def is_running(self) -> bool:
        return self.state == RunState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == RunState.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self.state == RunState.STOPPED

    def start(self) -> None:
        """标记为运行中"""
        self.state = RunState.RUNNING

    def pause(self) -> None:
        """标记为暂停"""
        if self.state == RunState.RUNNING:
            self.state = RunState.PAUSED

    def resume(self) -> None:
        """从暂停恢复"""
        if self.state == RunState.PAUSED:
            self.state = RunState.RUNNING

    def stop(self) -> None:
        """标记为停止"""
        self.state = RunState.STOPPED

    # ── 日志 ──

    def log(self, message: str, level: str = "info") -> None:
        """记录一条日志"""
        import datetime
        self._logs.append({
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "message": message,
        })

    def get_logs(self, level: str | None = None) -> list[dict]:
        """获取日志列表，可按级别过滤"""
        if level:
            return [entry for entry in self._logs if entry["level"] == level]
        return list(self._logs)

    def clear_logs(self) -> None:
        """清空日志"""
        self._logs.clear()

    # ── 重置 ──

    def reset(self) -> None:
        """重置上下文（变量、缓存、日志全部清空，状态置为 STOPPED）"""
        self._vars.clear()
        self._screenshot_cache = None
        self._logs.clear()
        self.extras.clear()
        self.state = RunState.STOPPED
