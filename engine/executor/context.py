"""执行上下文 — 节点间共享的运行时状态

负责变量存储、截图缓存、日志收集和运行统计。
"""

from __future__ import annotations
import time
from typing import Any, Optional


class ExecutionContext:
    """执行上下文 — 在节点间传递的共享状态"""

    def __init__(self):
        self._variables: dict[str, Any] = {}
        self._node_outputs: dict[str, Any] = {}
        self._screenshots: dict[str, Any] = {}
        self._logs: list[dict] = []
        self._stats = {
            "executed_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "start_time": None,
            "elapsed_ms": 0,
            "current_node": None,
        }
        # 运行控制标志
        self.running = True
        self.paused = False
        self.stopped = False
        self.step_mode = False

    # ── 变量读写 ──

    def get_var(self, key: str, default: Any = None) -> Any:
        return self._variables.get(key, default)

    def set_var(self, key: str, value: Any):
        self._variables[key] = value

    def get_node_output(self, node_id: str) -> Any:
        return self._node_outputs.get(node_id)

    def set_node_output(self, node_id: str, value: Any):
        self._node_outputs[node_id] = value

    def get_all_variables(self) -> dict:
        return dict(self._variables)

    # ── 截图缓存 ──

    def cache_screenshot(self, key: str, image: Any):
        self._screenshots[key] = image

    def get_screenshot(self, key: str) -> Any:
        return self._screenshots.get(key)

    def clear_screenshots(self):
        self._screenshots.clear()

    # ── 日志收集 ──

    def log(self, level: str, message: str,
            node_id: str = "", data: Any = None) -> dict:
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "node_id": node_id,
            "data": data,
        }
        self._logs.append(entry)
        return entry

    def info(self, message: str, node_id: str = "", data: Any = None):
        return self.log("INFO", message, node_id, data)

    def warn(self, message: str, node_id: str = "", data: Any = None):
        return self.log("WARN", message, node_id, data)

    def error(self, message: str, node_id: str = "", data: Any = None):
        return self.log("ERROR", message, node_id, data)

    def get_logs(self) -> list[dict]:
        return list(self._logs)

    def get_recent_logs(self, count: int = 50) -> list[dict]:
        return self._logs[-count:] if self._logs else []

    # ── 统计 ──

    @property
    def stats(self) -> dict:
        d = dict(self._stats)
        if self._stats["start_time"]:
            d["elapsed_ms"] = int(
                (time.time() - self._stats["start_time"]) * 1000
            )
        return d

    def mark_start(self):
        self._stats["start_time"] = time.time()
        self._stats["executed_count"] = 0
        self._stats["success_count"] = 0
        self._stats["failed_count"] = 0

    def mark_executed(self, node_id: str, success: bool):
        self._stats["executed_count"] += 1
        if success:
            self._stats["success_count"] += 1
        else:
            self._stats["failed_count"] += 1
        self._stats["current_node"] = node_id

    def mark_current_node(self, node_id: Optional[str]):
        self._stats["current_node"] = node_id

    # ── 状态控制 ──

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.stopped = True
        self.running = False

    def enable_step_mode(self):
        self.step_mode = True
        self.paused = True  # 单步模式开始时先暂停

    def step_once(self):
        """单步执行：放行，执行一个节点后自动恢复暂停"""
        self.paused = False

    def is_active(self) -> bool:
        """是否仍在运行中"""
        return self.running and not self.stopped
