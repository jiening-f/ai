"""
执行上下文

提供脚本执行期间的变量存储、服务访问、截图缓存、日志记录和运行状态管理。

变量存储支持：
- 全局变量（跨节点持久）
- 临时节点输出（仅当前节点执行后可用）

服务访问：
- 通过 get_service(name) 获取注册的服务（如 keyboard、mouse、ocr 等）
"""

import time
from enum import Enum
from typing import Any
import numpy as np


class ExecutionStatus(Enum):
    """执行状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class ExecutionContext:
    """脚本执行上下文，贯穿整个脚本生命周期"""

    def __init__(self, execution_id: str | None = None):
        self.execution_id = execution_id or ""
        self.status: ExecutionStatus = ExecutionStatus.IDLE

        # 变量存储
        self._variables: dict[str, Any] = {}
        self._temp_output: dict[str, Any] = {}

        # 截图缓存（numpy array 或 None）
        self._screenshot: np.ndarray | None = None

        # 日志记录
        self._logs: list[dict] = []

        # 运行统计
        self._node_count: int = 0
        self._start_time: float = 0.0
        self._current_node_id: str = ""

        # 服务注册表（keyboard、mouse、ocr、template_matcher、screenshot、window）
        self._services: dict[str, Any] = {}

        # 截图截图（可配置最大缓存数量）
        self._screenshot_cache: list[np.ndarray] = []
        self._max_screenshot_cache: int = 10

    # ── 变量操作 ──────────────────────

    def get_var(self, name: str, default: Any = None) -> Any:
        """获取变量值，优先返回临时输出，其次全局变量"""
        if name in self._temp_output:
            return self._temp_output[name]
        return self._variables.get(name, default)

    def set_var(self, name: str, value: Any):
        """设置全局变量"""
        self._variables[name] = value

    def set_temp(self, name: str, value: Any):
        """设置临时输出（当前节点后即清除）"""
        self._temp_output[name] = value

    def clear_temp(self):
        """清除所有临时输出"""
        self._temp_output.clear()

    def get_all_vars(self) -> dict:
        """获取所有变量（合并临时和全局）"""
        merged = dict(self._variables)
        merged.update(self._temp_output)
        return merged

    # ── 截图管理 ──────────────────────

    @property
    def screenshot(self) -> np.ndarray | None:
        """获取当前截图缓存"""
        return self._screenshot

    @screenshot.setter
    def screenshot(self, img: np.ndarray | None):
        """设置当前截图，同时加入缓存"""
        if img is not None:
            self._screenshot = img
            self._screenshot_cache.append(img)
            if len(self._screenshot_cache) > self._max_screenshot_cache:
                self._screenshot_cache.pop(0)

    def get_last_screenshot(self, offset: int = 0) -> np.ndarray | None:
        """获取历史截图缓存"""
        idx = -1 - offset
        if len(self._screenshot_cache) > abs(idx) - 1:
            return self._screenshot_cache[idx]
        return None

    # ── 日志收集 ──────────────────────

    def log(self, message: str, level: str = "INFO"):
        """记录一条执行日志"""
        entry = {
            "time": time.time(),
            "level": level,
            "message": message,
            "node_id": self._current_node_id,
        }
        self._logs.append(entry)

    def get_logs(self, tail: int = 0) -> list[dict]:
        """获取日志（支持取最近 N 条）"""
        if tail > 0:
            return self._logs[-tail:]
        return list(self._logs)

    # ── 运行统计 ──────────────────────

    @property
    def node_count(self) -> int:
        return self._node_count

    @property
    def current_node_id(self) -> str:
        return self._current_node_id

    @current_node_id.setter
    def current_node_id(self, node_id: str):
        self._current_node_id = node_id

    @property
    def elapsed_ms(self) -> float:
        if self._start_time == 0:
            return 0
        return (time.time() - self._start_time) * 1000

    @property
    def has_started(self) -> bool:
        """定时器是否已启动"""
        return self._start_time != 0.0

    def start_timer(self):
        self._start_time = time.time()

    def increment_node_count(self):
        self._node_count += 1

    # ── 服务注册 ──────────────────────

    def register_service(self, name: str, service: Any):
        """
        注册一个系统服务（如键盘、鼠标、OCR 等）

        Args:
            name: 服务名称（keyboard、mouse、ocr、template_matcher、screenshot、window）
            service: 服务实例
        """
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """获取已注册的服务"""
        return self._services.get(name)

    # ── 状态管理 ──────────────────────

    def is_running(self) -> bool:
        return self.status == ExecutionStatus.RUNNING

    def is_paused(self) -> bool:
        return self.status == ExecutionStatus.PAUSED

    def is_stopped(self) -> bool:
        return self.status == ExecutionStatus.STOPPED

    def should_stop(self) -> bool:
        """运行循环应检查此标记"""
        return self.status in (ExecutionStatus.STOPPED, ExecutionStatus.ERROR)

    def reset(self):
        """重置上下文状态"""
        self.status = ExecutionStatus.IDLE
        self._variables.clear()
        self._temp_output.clear()
        self._screenshot = None
        self._screenshot_cache.clear()
        self._logs.clear()
        self._node_count = 0
        self._start_time = 0.0
        self._current_node_id = ""
