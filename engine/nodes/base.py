"""节点基类和结果类型定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


class NodeStatus(Enum):
    """节点执行结果状态。"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    """节点执行返回结果。"""
    status: NodeStatus
    next_node: str | None = None        # 指定下一个节点 ID（覆盖默认连线）
    data: dict[str, Any] = field(default_factory=dict)   # 输出数据，写入上下文变量
    error: str | None = None            # 失败时的错误信息


class BaseNode(ABC):
    """所有脚本节点的抽象基类。

    子类必须实现 execute() 和 validate()。
    通过 node_type 类属性注册到 NODE_REGISTRY。
    """

    # 子类覆盖 —— 注册时使用
    node_type: str = ""
    node_category: str = ""
    node_description: str = ""

    # 默认配置 schema —— 子类覆盖
    default_config: dict[str, Any] = {}

    def __init__(
        self,
        node_id: str,
        config: dict[str, Any] | None = None,
        next_nodes: list[str] | None = None,
        condition: str | None = None,
    ):
        self.node_id = node_id
        self.config = {**self.default_config, **(config or {})}
        self.next_nodes = next_nodes or []
        self.condition = condition

    @abstractmethod
    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        """执行节点逻辑。子类必须实现。"""
        ...

    def validate(self) -> bool:
        """验证节点配置是否合法。默认检查必要字段。"""
        return True

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 JSON 存储）。"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "config": self.config,
            "next_nodes": self.next_nodes,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseNode:
        """从字典反序列化。"""
        return cls(
            node_id=data["node_id"],
            config=data.get("config"),
            next_nodes=data.get("next_nodes", []),
            condition=data.get("condition"),
        )

    def __repr__(self) -> str:
        return f"<{self.node_type}:{self.node_id}>"
