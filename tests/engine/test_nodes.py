"""测试 engine/nodes/ — 所有节点类型的创建、验证和执行

覆盖节点类型：
  BaseNode, StartNode, EndNode, WaitNode, LogNode, ConditionNode, LoopNode
以及枚举和数据类：
  NodeStatus, NodeResult
"""

import pytest
import asyncio

from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.nodes.flow import (
    StartNode, EndNode, WaitNode, LogNode, ConditionNode, LoopNode,
)
from engine.executor.context import ExecutionContext


# ═══════════════════════════════════════════════════════════════
# NodeStatus 和 NodeResult 测试
# ═══════════════════════════════════════════════════════════════

class TestNodeStatus:
    """测试 NodeStatus 枚举"""

    def test_all_status_values(self):
        """验证所有状态值存在且唯一"""
        values = {s.value for s in NodeStatus}
        assert "success" in values
        assert "failed" in values
        assert "skipped" in values
        assert "waiting" in values
        assert len(values) == 4

    def test_status_equality(self):
        """验证状态比较"""
        assert NodeStatus.SUCCESS == NodeStatus("success")
        assert NodeStatus.FAILED == NodeStatus("failed")
        assert NodeStatus.SUCCESS != NodeStatus.FAILED

    def test_status_is_truthy_for_success(self):
        """只有 SUCCESS 状态代表执行成功"""
        assert NodeStatus.SUCCESS.value == "success"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"
        assert NodeStatus.WAITING.value == "waiting"


class TestNodeResult:
    """测试 NodeResult 数据类"""

    def test_create_success_result(self):
        result = NodeResult(status=NodeStatus.SUCCESS, data={"key": "value"})
        assert result.status == NodeStatus.SUCCESS
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.next_node is None

    def test_create_failed_result(self):
        result = NodeResult(status=NodeStatus.FAILED, error="something went wrong")
        assert result.status == NodeStatus.FAILED
        assert result.data is None
        assert result.error == "something went wrong"

    def test_create_result_with_next_node(self):
        result = NodeResult(status=NodeStatus.SUCCESS, next_node="node_5")
        assert result.next_node == "node_5"

    def test_result_defaults(self):
        result = NodeResult(status=NodeStatus.SKIPPED)
        assert result.data is None
        assert result.error is None
        assert result.next_node is None


# ═══════════════════════════════════════════════════════════════
# BaseNode 测试
# ═══════════════════════════════════════════════════════════════

class TestBaseNode:
    """测试 BaseNode 抽象基类"""

    def test_base_node_attributes(self):
        """验证基础属性"""
        node = StartNode("my_id")
        assert node.node_id == "my_id"
        assert node.node_type == "start"
        assert node.config == {}
        assert node.next_nodes == []
        assert node.condition is None

    def test_base_node_with_config(self):
        """验证带配置的构造"""
        node = WaitNode("w1", {"duration": 2.5})
        assert node.config == {"duration": 2.5}

    def test_validate_default(self):
        """默认 validate 检查 node_id 非空"""
        node = StartNode("test")
        assert node.validate() is True

    def test_validate_empty_id(self):
        """空 node_id 应验证失败"""
        node = StartNode("")
        assert node.validate() is False

    def test_get_next_node_default(self):
        """默认 get_next_node 返回 next_nodes[0]"""
        node = StartNode("start")
        node.next_nodes = ["step1", "step2"]
        result = NodeResult(status=NodeStatus.SUCCESS)
        assert node.get_next_node(result) == "step1"

    def test_get_next_node_explicit(self):
        """result.next_node 覆盖默认"""
        node = StartNode("start")
        node.next_nodes = ["step1"]
        result = NodeResult(status=NodeStatus.SUCCESS, next_node="override")
        assert node.get_next_node(result) == "override"

    def test_get_next_node_empty(self):
        """无后续节点时返回 None"""
        node = StartNode("start")
        result = NodeResult(status=NodeStatus.SUCCESS)
        assert node.get_next_node(result) is None

    def test_to_dict(self):
        """测试序列化"""
        node = StartNode("n1")
        node.next_nodes = ["n2"]
        node.condition = "x > 5"
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["node_type"] == "start"
        assert d["config"] == {}
        assert d["next_nodes"] == ["n2"]
        assert d["condition"] == "x > 5"

    def test_repr(self):
        node = StartNode("my_start")
        assert repr(node) == "start(my_start)"


# ═══════════════════════════════════════════════════════════════
# StartNode 测试
# ═══════════════════════════════════════════════════════════════

class TestStartNode:
    """测试 StartNode（类型 1）"""

    def test_node_type(self):
        node = StartNode("start")
        assert node.node_type == "start"

    def test_validate(self):
        node = StartNode("start")
        assert node.validate() is True

    @pytest.mark.asyncio
    async def test_execute_returns_success(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        node = StartNode("start")
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_logs_info(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        node = StartNode("start")
        await node.execute(ctx)
        logs = ctx.get_logs()
        assert len(logs) >= 1
        assert "流程开始" in logs[0]["message"]


# ═══════════════════════════════════════════════════════════════
# EndNode 测试
# ═══════════════════════════════════════════════════════════════

class TestEndNode:
    """测试 EndNode（类型 2）"""

    def test_node_type(self):
        node = EndNode("end")
        assert node.node_type == "end"

    def test_validate(self):
        node = EndNode("end")
        assert node.validate() is True

    @pytest.mark.asyncio
    async def test_execute_returns_success_with_none_next(self):
        ctx = ExecutionContext()
        node = EndNode("end")
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS
        assert result.next_node is None  # 明确终止流程

    @pytest.mark.asyncio
    async def test_execute_logs_end(self):
        ctx = ExecutionContext()
        node = EndNode("end")
        await node.execute(ctx)
        logs = ctx.get_logs()
        assert any("流程结束" in log["message"] for log in logs)


# ═══════════════════════════════════════════════════════════════
# WaitNode 测试
# ═══════════════════════════════════════════════════════════════

class TestWaitNode:
    """测试 WaitNode（类型 3）"""

    def test_node_type(self):
        node = WaitNode("w1", {"duration": 1.0})
        assert node.node_type == "wait"

    def test_validate_positive_duration(self):
        assert WaitNode("w1", {"duration": 2.5}).validate() is True

    def test_validate_zero_duration(self):
        assert WaitNode("w1", {"duration": 0}).validate() is True

    def test_validate_negative_duration(self):
        assert WaitNode("w1", {"duration": -1}).validate() is False

    def test_validate_missing_duration(self):
        # duration 默认值为 0，0 >= 0 是合法的
        assert WaitNode("w1", {}).validate() is True

    def test_validate_non_numeric_duration(self):
        assert WaitNode("w1", {"duration": "abc"}).validate() is False

    @pytest.mark.asyncio
    async def test_execute_waits(self):
        ctx = ExecutionContext()
        node = WaitNode("w1", {"duration": 0.05})
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_default_duration(self):
        ctx = ExecutionContext()
        node = WaitNode("w1", {})
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS  # 默认 1 秒，会等待


# ═══════════════════════════════════════════════════════════════
# LogNode 测试
# ═══════════════════════════════════════════════════════════════

class TestLogNode:
    """测试 LogNode（类型 4）"""

    def test_node_type(self):
        node = LogNode("log1")
        assert node.node_type == "log"

    @pytest.mark.asyncio
    async def test_execute_with_message(self):
        ctx = ExecutionContext()
        node = LogNode("log1", {"message": "hello world", "level": "WARN"})
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS

        logs = ctx.get_logs()
        assert len(logs) == 1
        assert logs[0]["message"] == "hello world"
        assert logs[0]["level"] == "WARN"
        assert logs[0]["node_id"] == "log1"

    @pytest.mark.asyncio
    async def test_execute_default_message(self):
        ctx = ExecutionContext()
        node = LogNode("log1", {})
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS
        logs = ctx.get_logs()
        assert logs[0]["message"] == ""
        assert logs[0]["level"] == "INFO"

    def test_validate(self):
        node = LogNode("log1")
        assert node.validate() is True


# ═══════════════════════════════════════════════════════════════
# ConditionNode 测试
# ═══════════════════════════════════════════════════════════════

class TestConditionNode:
    """测试 ConditionNode（类型 5）"""

    def test_node_type(self):
        node = ConditionNode("cond1")
        assert node.node_type == "condition"

    @pytest.mark.asyncio
    async def test_evaluate_true(self):
        ctx = ExecutionContext()
        ctx.set_var("score", 100)
        node = ConditionNode("cond1", {
            "condition": "vars['score'] > 50",
            "true_branch": "path_a",
            "false_branch": "path_b",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_evaluate_false(self):
        ctx = ExecutionContext()
        node = ConditionNode("cond1", {
            "condition": "False",
            "true_branch": "path_a",
            "false_branch": "path_b",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_evaluate_bad_expression(self):
        ctx = ExecutionContext()
        node = ConditionNode("cond1", {
            "condition": "undefined_var + 1",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.FAILED
        assert "条件表达式求值失败" in result.error

    def test_get_next_node_true(self):
        node = ConditionNode("cond1", {
            "true_branch": "yes_path",
            "false_branch": "no_path",
        })
        result = NodeResult(status=NodeStatus.SUCCESS)
        assert node.get_next_node(result) == "yes_path"

    def test_get_next_node_false(self):
        node = ConditionNode("cond1", {
            "true_branch": "yes_path",
            "false_branch": "no_path",
        })
        result = NodeResult(status=NodeStatus.SKIPPED)
        assert node.get_next_node(result) == "no_path"

    def test_get_next_node_fallback_to_next_nodes(self):
        """无配置分支时 fallback 到 next_nodes"""
        node = ConditionNode("cond1", {})
        node.next_nodes = ["a", "b"]
        assert node.get_next_node(NodeResult(status=NodeStatus.SUCCESS)) == "a"
        assert node.get_next_node(NodeResult(status=NodeStatus.SKIPPED)) == "b"

    @pytest.mark.asyncio
    async def test_condition_with_variables(self):
        ctx = ExecutionContext()
        ctx.set_var("hp", 30)
        ctx.set_var("max_hp", 100)
        node = ConditionNode("cond1", {
            "condition": "vars['hp'] < vars['max_hp'] * 0.5",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS  # 30 < 50


# ═══════════════════════════════════════════════════════════════
# LoopNode 测试
# ═══════════════════════════════════════════════════════════════

class TestLoopNode:
    """测试 LoopNode（类型 6）"""

    def test_node_type(self):
        node = LoopNode("loop1")
        assert node.node_type == "loop"

    @pytest.mark.asyncio
    async def test_should_loop(self):
        ctx = ExecutionContext()
        node = LoopNode("loop1", {
            "condition": "True",
            "loop_target": "start",
            "max_iterations": 100,
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS
        assert result.next_node == "start"
        assert ctx.get_var("_loop_loop1_count") == 1

    @pytest.mark.asyncio
    async def test_loop_counter_increments(self):
        ctx = ExecutionContext()
        ctx.set_var("_loop_my_loop_count", 2)
        node = LoopNode("my_loop", {
            "condition": "True",
            "loop_target": "step1",
            "max_iterations": 100,
        })
        result = await node.execute(ctx)
        assert ctx.get_var("_loop_my_loop_count") == 3

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self):
        ctx = ExecutionContext()
        ctx.set_var("_loop_lp_count", 5)
        node = LoopNode("lp", {
            "condition": "True",
            "loop_target": "step1",
            "max_iterations": 5,
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS
        assert result.next_node is None  # 不再循环

    @pytest.mark.asyncio
    async def test_condition_false_exits(self):
        ctx = ExecutionContext()
        node = LoopNode("loop1", {
            "condition": "False",
            "loop_target": "start",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.SUCCESS
        assert result.next_node is None  # 退出循环

    @pytest.mark.asyncio
    async def test_bad_expression(self):
        ctx = ExecutionContext()
        node = LoopNode("loop1", {
            "condition": "invalid_syntax[",
        })
        result = await node.execute(ctx)
        assert result.status == NodeStatus.FAILED
        assert "循环条件求值失败" in result.error

    @pytest.mark.asyncio
    async def test_variable_driven_loop(self):
        ctx = ExecutionContext()
        ctx.set_var("counter", 0)
        node = LoopNode("while_loop", {
            "condition": "vars['counter'] < 3",
            "loop_target": "increment",
        })
        # 第 1 次：counter=0 < 3 → 循环
        r1 = await node.execute(ctx)
        assert r1.status == NodeStatus.SUCCESS
        assert r1.next_node == "increment"

        # 模拟 counter 递增
        ctx.set_var("counter", 1)
        r2 = await node.execute(ctx)
        assert r2.next_node == "increment"

        ctx.set_var("counter", 2)
        r3 = await node.execute(ctx)
        assert r3.next_node == "increment"

        ctx.set_var("counter", 3)
        r4 = await node.execute(ctx)
        assert r4.next_node is None  # 退出

    def test_validate(self):
        node = LoopNode("loop1")
        assert node.validate() is True
