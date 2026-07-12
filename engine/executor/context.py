"""执行上下文 —— 脚本运行期间的共享状态。"""

from __future__ import annotations

from enum import Enum
from typing import Any


class RunState(Enum):
    """执行器运行状态。"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class ExecutionContext:
    """脚本执行期间的全局上下文。

    持有变量存储、当前截图缓存、运行状态和日志收集器。
    每个脚本运行实例创建一个新的 ExecutionContext。
    """

    def __init__(self):
        self.variables: dict[str, Any] = {}          # 变量存储
        self.screenshot_cache: Any = None            # 当前截图（numpy 数组或 None）
        self.state: RunState = RunState.IDLE         # 运行状态
        self.logs: list[str] = []                    # 执行日志
        self.start_time: float | None = None         # 开始时间（time.monotonic）
        self.node_results: dict[str, Any] = {}       # 各节点执行结果（node_id → NodeResult）

    # ── 变量操作 ──

    def set_var(self, key: str, value: Any) -> None:
        """设置变量。"""
        self.variables[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        """读取变量。"""
        return self.variables.get(key, default)

    def delete_var(self, key: str) -> None:
        """删除变量。"""
        self.variables.pop(key, None)

    # ── 日志 ──

    def log(self, message: str) -> None:
        """追加一条执行日志。"""
        self.logs.append(message)

    # ── 状态控制 ──

    @property
    def is_running(self) -> bool:
        return self.state == RunState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == RunState.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self.state == RunState.STOPPED

    def pause(self) -> None:
        if self.state == RunState.RUNNING:
            self.state = RunState.PAUSED

    def resume(self) -> None:
        if self.state == RunState.PAUSED:
            self.state = RunState.RUNNING

    def stop(self) -> None:
        self.state = RunState.STOPPED

    def start(self) -> None:
        import time
        self.state = RunState.RUNNING
        self.start_time = time.monotonic()

    # ── 快照 ──

    def snapshot(self) -> dict[str, Any]:
        """返回当前上下文快照（用于调试/序列化）。"""
        return {
            "state": self.state.value,
            "variables": dict(self.variables),
            "log_count": len(self.logs),
            "has_screenshot": self.screenshot_cache is not None,
        }
