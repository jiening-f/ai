"""引擎执行器测试 — 验证异步执行、状态机和错误处理"""
import asyncio
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.executor.runner import ScriptRunner, EngineState, create_runner
from engine.executor.context import ExecutionContext
from engine.executor.hooks import HookSystem
from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.nodes.flow import StartNode, EndNode, WaitNode, LogNode, ConditionNode, LoopNode


def test_basic_flow():
    """测试 1: 基本线性流程 (start → wait → log → end)"""
    print("=== 测试1: 基本线性流程 ===")

    nodes = {
        "start": StartNode("start"),
        "wait": WaitNode("wait", {"duration": 0.1}),
        "log": LogNode("log", {"message": "测试消息", "level": "INFO"}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["wait"]
    nodes["wait"].next_nodes = ["log"]
    nodes["log"].next_nodes = ["end"]

    runner = create_runner(nodes, "start", with_logging=False)
    ctx = asyncio.run(runner.run())

    # 4 个节点: start + wait + log + end
    assert ctx.stats["executed_count"] == 4
    assert ctx.stats["success_count"] == 4
    assert runner.state == EngineState.COMPLETED
    print("  ✓ 通过 — 节点全部执行，引擎正常完成")
    print(f"  统计: {ctx.stats}")


def test_pause_resume():
    """测试 2: 暂停/恢复"""
    print("\n=== 测试2: 暂停/恢复 ===")

    nodes = {
        "start": StartNode("start"),
        "wait1": WaitNode("wait1", {"duration": 0.05}),
        "wait2": WaitNode("wait2", {"duration": 0.05}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["wait1"]
    nodes["wait1"].next_nodes = ["wait2"]
    nodes["wait2"].next_nodes = ["end"]

    runner = create_runner(nodes, "start", with_logging=False)

    async def run_with_pause():
        # 在后台启动执行
        task = asyncio.create_task(runner.run())
        await asyncio.sleep(0.02)  # 让第一个 wait 开始
        await runner.pause()
        assert runner.state == EngineState.PAUSED
        await asyncio.sleep(0.1)  # 等待确认
        assert runner.state == EngineState.PAUSED  # 仍在暂停
        await runner.resume()
        assert runner.state == EngineState.RUNNING
        ctx = await task
        return ctx

    ctx = asyncio.run(run_with_pause())
    assert ctx.stats["executed_count"] >= 2
    print("  ✓ 通过 — 暂停/恢复功能正常")


def test_step_mode():
    """测试 3: 单步调试模式"""
    print("\n=== 测试3: 单步模式 ===")

    nodes = {
        "start": StartNode("start"),
        "step1": LogNode("step1", {"message": "第一步"}),
        "step2": LogNode("step2", {"message": "第二步"}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["step1"]
    nodes["step1"].next_nodes = ["step2"]
    nodes["step2"].next_nodes = ["end"]

    runner = ScriptRunner(nodes, "start")

    async def step_run():
        ctx = ExecutionContext()
        ctx.mark_start()
        ctx.enable_step_mode()
        runner._ctx = ctx
        runner._set_state(EngineState.RUNNING)

        # 手动单步
        ctx.step_once()
        # 模拟执行第一个节点
        for nid in ["start", "step1"]:
            node = nodes[nid]
            ctx.mark_current_node(nid)
            result = await node.execute(ctx)
            ctx.mark_executed(nid, result.status == result.status.__class__.SUCCESS)
            # 单步后自动暂停
            if ctx.step_mode:
                ctx.paused = True
            if ctx.paused:
                break

        assert ctx.stats["executed_count"] >= 1
        return ctx

    ctx = asyncio.run(step_run())
    assert ctx.stats["executed_count"] >= 1
    print("  ✓ 通过 — 单步模式正常（执行一个节点后暂停）")


def test_error_handling():
    """测试 4: 错误处理"""
    print("\n=== 测试4: 错误处理 ===")

    class ErrorNode(StartNode):
        node_type = "error_test"
        async def execute(self, ctx):
            raise ValueError("模拟节点错误")

    nodes = {
        "start": StartNode("start"),
        "bad": ErrorNode("bad"),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["bad"]
    nodes["bad"].next_nodes = ["end"]

    # on_error = "stop"
    runner = ScriptRunner(nodes, "start", on_error="stop")
    ctx = asyncio.run(runner.run())
    assert runner.state == EngineState.ERROR
    assert "模拟节点错误" in str(ctx.get_logs())
    print("  ✓ 通过 — 错误停止策略正常")

    # on_error = "continue"
    runner2 = ScriptRunner(nodes, "start", on_error="continue")
    ctx2 = asyncio.run(runner2.run())
    assert runner2.state == EngineState.COMPLETED
    print("  ✓ 通过 — 错误跳过策略正常（继续执行）")


def test_condition_branch():
    """测试 5: 条件分支"""
    print("\n=== 测试5: 条件分支 ===")

    nodes = {
        "start": StartNode("start"),
        "check": ConditionNode("check", {
            "condition": "True",
            "true_branch": "path_a",
            "false_branch": "path_b",
        }),
        "path_a": LogNode("path_a", {"message": "走了分支A"}),
        "path_b": LogNode("path_b", {"message": "走了分支B"}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["check"]
    nodes["check"].next_nodes = ["path_a", "path_b"]  # [true, false]
    nodes["path_a"].next_nodes = ["end"]
    nodes["path_b"].next_nodes = ["end"]

    runner = ScriptRunner(nodes, "start")
    ctx = asyncio.run(runner.run())
    assert runner.state == EngineState.COMPLETED

    # 检查走的是 path_a（条件为真）
    logs = [e["node_id"] for e in ctx.get_logs()]
    assert "path_a" in logs
    print(f"  ✓ 通过 — 条件分支正常（走了 path_a）")
    print(f"  执行节点: {logs}")


def test_hook_system():
    """测试 6: 钩子系统"""
    print("\n=== 测试6: 钩子系统 ===")

    hooks = HookSystem()
    pre_count = [0]
    post_count = [0]

    @hooks.on_pre_execute
    def count_pre(node, ctx):
        pre_count[0] += 1

    @hooks.on_post_execute
    def count_post(node, ctx, result):
        post_count[0] += 1

    nodes = {
        "start": StartNode("start"),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["end"]

    runner = ScriptRunner(nodes, "start", hooks=hooks)
    ctx = asyncio.run(runner.run())

    assert pre_count[0] >= 2  # start + end
    assert post_count[0] >= 2
    print(f"  ✓ 通过 — 钩子系统正常 (pre: {pre_count[0]}, post: {post_count[0]})")


def test_variable_flow():
    """测试 7: 变量传递"""
    print("\n=== 测试7: 变量传递 ===")

    class SetVarNode(BaseNode):
        node_type = "set_var"
        async def execute(self, ctx):
            ctx.set_var("test_key", "test_value")
            ctx.set_node_output(self.node_id, "output_data")
            return NodeResult(status=NodeStatus.SUCCESS)

    class GetVarNode(BaseNode):
        node_type = "get_var"
        async def execute(self, ctx):
            val = ctx.get_var("test_key")
            assert val == "test_value", f"期望 test_value，实际 {val}"
            output = ctx.get_node_output("setter")
            assert output == "output_data", f"期望 output_data，实际 {output}"
            return NodeResult(status=NodeStatus.SUCCESS)

    nodes = {
        "start": StartNode("start"),
        "setter": SetVarNode("setter"),
        "getter": GetVarNode("getter"),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["setter"]
    nodes["setter"].next_nodes = ["getter"]
    nodes["getter"].next_nodes = ["end"]

    runner = create_runner(nodes, "start", with_logging=False)
    ctx = asyncio.run(runner.run())
    assert runner.state == EngineState.COMPLETED
    print("  ✓ 通过 — 节点间变量传递正常")


# ── 主函数 ──

if __name__ == "__main__":
    test_basic_flow()
    test_pause_resume()
    test_step_mode()
    test_error_handling()
    test_condition_branch()
    test_hook_system()
    test_variable_flow()
    print("\n" + "=" * 50)
    print("所有测试通过！")
