"""节点基类定义 — 所有脚本节点的抽象基类"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class NodeStatus(Enum):
    """节点执行结果状态"""
    SUCCESS = "success"       # 执行成功，继续下一个节点
    FAILED = "failed"         # 执行失败
    SKIPPED = "skipped"       # 跳过（条件不满足）
    WAITING = "waiting"       # 等待中（异步操作未完成）


@dataclass
class NodeResult:
    """节点执行结果"""
    status: NodeStatus
    data: Any = None              # 节点输出数据
    error: Optional[str] = None   # 错误信息
    next_node: Optional[str] = None  # 指定下一个节点（覆盖默认流程）


class BaseNode(ABC):
    """脚本节点基类

    所有节点类型（开始/按键/OCR识别等）都继承此类。
    子类需要定义 node_type 并实现 execute() 方法。
    """

    node_type: str = "base"

    def __init__(self, node_id: str, config: Optional[dict] = None):
        self.node_id = node_id
        self.config = config or {}
        self.next_nodes: list[str] = []     # 默认后续节点
        self.condition: Optional[str] = None  # 条件表达式（条件节点用）

    @abstractmethod
    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        """执行节点逻辑（子类必须实现）"""
        ...

    def validate(self) -> bool:
        """验证节点配置是否合法（子类可覆盖）"""
        return bool(self.node_id)

    def get_next_node(self, result: NodeResult) -> Optional[str]:
        """根据执行结果决定下一个节点（条件节点覆盖此方法）"""
        if result.next_node:
            return result.next_node
        if self.next_nodes:
            return self.next_nodes[0]
        return None

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "config": self.config,
            "next_nodes": self.next_nodes,
            "condition": self.condition,
        }

    def __repr__(self) -> str:
        return f"{self.node_type}({self.node_id})"
