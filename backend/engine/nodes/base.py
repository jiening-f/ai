"""节点基类 — BaseNode 抽象基类 + NodeResult 数据类"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


@dataclass
class NodeResult:
    """节点执行结果

    Attributes:
        success: 是否执行成功
        next_node: 显式指定下一个节点 ID（为 None 时按 next_nodes 列表顺序执行）
        data: 输出数据（如 OCR 识别结果、截图路径等）
        error: 错误信息（success=False 时填充）
    """
    success: bool = True
    next_node: str | None = None
    data: dict = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def ok(cls, next_node: str | None = None, **data) -> "NodeResult":
        """快捷构造成功结果"""
        return cls(success=True, next_node=next_node, data=data)

    @classmethod
    def fail(cls, error: str, **data) -> "NodeResult":
        """快捷构造失败结果"""
        return cls(success=False, error=error, data=data)


class BaseNode(ABC):
    """脚本节点抽象基类

    所有节点类型必须继承此类并实现 execute() 方法。

    Attributes:
        node_id: 节点唯一标识
        node_type: 节点类型字符串（如 "key_press", "ocr_recognize"）
        config: 节点配置字典
        next_nodes: 下一个节点 ID 列表（默认按顺序执行第一个）
        condition: 条件表达式字符串（条件节点用于分支判断）

    Class Attributes（子类覆盖）:
        default_config: 默认配置 schema 字典
    """

    # 子类覆盖：默认配置 schema
    default_config: dict = {}

    def __init__(
        self,
        node_id: str = "",
        node_type: str = "",
        config: dict | None = None,
        next_nodes: list[str] | None = None,
        condition: str | None = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config or dict(self.default_config)
        self.next_nodes = next_nodes or []
        self.condition = condition

    @abstractmethod
    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        """执行节点逻辑

        Args:
            ctx: 执行上下文（变量、截图缓存、运行状态等）

        Returns:
            NodeResult: 执行结果
        """
        ...

    def validate(self) -> bool:
        """校验节点配置是否合法

        基类实现检查 config 中的必填字段是否存在。
        子类可覆盖以添加更严格的校验逻辑。

        Returns:
            bool: 配置是否合法
        """
        if not self.default_config:
            return True
        for key, default_val in self.default_config.items():
            if default_val is ...:  # ... (Ellipsis) 表示必填
                if key not in self.config or self.config[key] is None:
                    return False
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.node_id!r}, type={self.node_type!r})>"
