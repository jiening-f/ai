"""
节点基类定义

BaseNode: 所有脚本节点的抽象基类
NodeResult: 节点执行结果
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.executor.context import ExecutionContext


@dataclass
class NodeResult:
    """节点执行结果"""

    success: bool = True
    """执行是否成功"""

    next_node_id: str | None = None
    """覆盖默认的下一个节点 ID（条件分支/循环跳转时使用）"""

    data: dict = field(default_factory=dict)
    """节点输出的数据，合并到执行上下文变量中"""

    error_message: str = ""
    """失败时的错误信息"""


class BaseNode(ABC):
    """
    脚本节点抽象基类

    所有节点类型必须继承此类并实现 execute() 和 validate() 方法。
    """

    # 子类必须设置
    node_type: str = ""

    def __init__(
        self,
        node_id: str,
        config: dict | None = None,
        next_nodes: list[str] | None = None,
        condition: str | None = None,
    ):
        self.node_id = node_id
        self.config = config or {}
        self.next_nodes = next_nodes or []
        self.condition = condition

    @abstractmethod
    async def execute(self, ctx: "ExecutionContext") -> NodeResult:
        """
        执行节点逻辑

        子类实现具体的节点行为。调用 ctx 访问变量、截图缓存、日志等。

        Args:
            ctx: 执行上下文

        Returns:
            NodeResult: 执行结果
        """
        ...

    def validate(self) -> bool:
        """
        验证节点配置是否合法

        默认返回 True。子类可重写以检查必要字段。

        Returns:
            bool: 配置有效为 True
        """
        return True

    @classmethod
    def default_config(cls) -> dict:
        """返回节点的默认配置模板"""
        return {}

    @classmethod
    def description(cls) -> dict:
        """
        返回节点元数据（名称、分类、描述、配置 schema）
        """
        return {
            "type": cls.node_type,
            "name": cls.__name__,
            "category": "other",
            "description": "",
            "config_schema": cls.default_config(),
        }
