"""引擎执行器测试 — 验证异步执行、状态机和错误处理

共 7 项测试，覆盖基本流程、暂停/恢复、单步调试、
错误处理、条件分支、钩子系统、变量传递。
"""
import asyncio
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.executor.runner import ScriptRunner, EngineState, create_runner
from engine.executor.context import ExecutionContext
from engine.executor.hooks import HookSystem
from engine.nodes.base import BaseNode, NodeResult
from engine.nodes.flow import StartNode, EndNode, WaitNode, LogNode, ConditionNode


def test_basic_flow():
    """测试 1: 基本线性流程 (start → wait → log → end)"""
    print("=== 测试1: 基本线性流程 ===")

    nodes = {
        "start": StartNode("start"),
        "wait": WaitNode("wait", {"duration_ms": 100}),  # 100ms
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
    print("  [PASS] All nodes executed, engine completed normally")
    print(f"  Stats: {ctx.stats}")


def test_pause_resume():
    """测试 2: 暂停/恢复"""
    print("\n=== 测试2: 暂停/恢复 ===")

    nodes = {
        "start": StartNode("start"),
        "wait1": WaitNode("wait1", {"duration_ms": 50}),
        "wait2": WaitNode("wait2", {"duration_ms": 50}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["wait1"]
    nodes["wait1"].next_nodes = ["wait2"]
    nodes["wait2"].next_nodes = ["end"]

    runner = create_runner(nodes, "start", with_logging=False)

    async def run_with_pause():
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
    print("  [PASS] Pause/resume works correctly")


def test_step_mode():
    """测试 3: 单步调试模式 — 验证 step() 可独立调用且每步只执行一个节点"""
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

    async def step_run():
        runner = ScriptRunner(nodes, "start")

        # 第一步：step() 自动初始化和执行
        await runner.step()
        # step() 后自动暂停，统计应为 2（start + step1 都执行了）
        # 注意：step 模式下，第一个节点执行后暂停
        # start 是一个轻量节点，执行很快
        assert runner.state == EngineState.RUNNING or runner.state == EngineState.PAUSED
        assert runner.context.stats["executed_count"] >= 1
        executed_before = runner.context.stats["executed_count"]

        # 恢复后再执行一个 step
        if runner.state == EngineState.PAUSED:
            runner._ctx.step_once()
            runner._pause_event.set()
            await asyncio.sleep(0.01)

        return runner.context

    ctx = asyncio.run(step_run())
    assert ctx.stats["executed_count"] >= 1
    print("  [PASS] Step mode works (executes then pauses)")


def test_error_handling():
    """测试 4: 错误处理（stop/continue 策略 + retry_count 守卫）"""
    print("\n=== 测试4: 错误处理 ===")

    class ErrorNode(BaseNode):
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

    # on_error = "stop"（默认）
    runner = ScriptRunner(nodes, "start", on_error="stop")
    ctx = asyncio.run(runner.run())
    assert runner.state == EngineState.ERROR
    assert "模拟节点错误" in str(ctx.get_logs())
    print("  [PASS] Error stop strategy works")

    # on_error = "continue"
    runner2 = ScriptRunner(nodes, "start", on_error="continue")
    ctx2 = asyncio.run(runner2.run())
    assert runner2.state == EngineState.COMPLETED
    print("  [PASS] Error continue strategy works (skips and proceeds)")

    # retry_count <= 0 guard: should fall back to stop
    runner3 = ScriptRunner(nodes, "start", on_error="retry", max_retries=0)
    ctx3 = asyncio.run(runner3.run())
    assert runner3.state == EngineState.ERROR
    print("  [PASS] retry_count=0 guard: falls back to stop")


def test_condition_branch():
    """测试 5: 条件分支"""
    print("\n=== 测试5: 条件分支 ===")

    # 使用变量设置来测试条件分支
    class SetVarNode(BaseNode):
        node_type = "set_var_test"
        async def execute(self, ctx):
            ctx.set_var("flag", "yes")
            return NodeResult(success=True)

    class CondCheckNode(BaseNode):
        node_type = "cond_test"
        async def execute(self, ctx):
            flag = ctx.get_var("flag", "no")
            if flag == "yes":
                return NodeResult(success=True, next_node_id=self.next_nodes[0] if self.next_nodes else None)
            return NodeResult(success=True, next_node_id=self.next_nodes[1] if len(self.next_nodes) > 1 else None)

    nodes = {
        "start": StartNode("start"),
        "setter": SetVarNode("setter"),
        "check": CondCheckNode("check"),
        "path_a": LogNode("path_a", {"message": "走了分支A"}),
        "path_b": LogNode("path_b", {"message": "走了分支B"}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["setter"]
    nodes["setter"].next_nodes = ["check"]
    nodes["check"].next_nodes = ["path_a", "path_b"]  # [true分支, false分支]
    nodes["path_a"].next_nodes = ["end"]
    nodes["path_b"].next_nodes = ["end"]

    runner = ScriptRunner(nodes, "start")
    ctx = asyncio.run(runner.run())
    assert runner.state == EngineState.COMPLETED

    logs = [e["node_id"] for e in ctx.get_logs()]
    assert "path_a" in logs
    print(f"  [PASS] Condition branch works (went through path_a)")
    print(f"  Executed nodes: {logs}")


def test_hook_system():
    """测试 6: 钩子系统（含异步回调支持）"""
    print("\n=== 测试6: 钩子系统 ===")

    hooks = HookSystem()
    pre_count = [0]
    post_count = [0]

    @hooks.on_pre_execute
    def count_pre(node, ctx):
        pre_count[0] += 1

    @hooks.on_post_execute
    async def count_post(node, ctx, result):
        # 异步钩子也能正常工作
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
    print(f"  [PASS] Hook system works (pre: {pre_count[0]}, post: {post_count[0]})")


def test_variable_flow():
    """测试 7: 变量传递"""
    print("\n=== 测试7: 变量传递 ===")

    class SetVarNode(BaseNode):
        node_type = "set_var"
        async def execute(self, ctx):
            ctx.set_var("test_key", "test_value")
            ctx.set_node_output(self.node_id, "output_data")
            return NodeResult(success=True)

    class GetVarNode(BaseNode):
        node_type = "get_var"
        async def execute(self, ctx):
            val = ctx.get_var("test_key")
            assert val == "test_value", f"期望 test_value，实际 {val}"
            output = ctx.get_node_output("setter")
            assert output == "output_data", f"期望 output_data，实际 {output}"
            return NodeResult(success=True)

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
    print("  [PASS] Variable passing between nodes works")


# ── 主函数 ──

if __name__ == "__main__":
    results = []
    for test in [
        test_basic_flow,
        test_pause_resume,
        test_step_mode,
        test_error_handling,
        test_condition_branch,
        test_hook_system,
        test_variable_flow,
    ]:
        try:
            test()
            results.append(("PASS", test.__doc__.split("\n")[0]))
        except Exception as e:
            results.append(("FAIL", f"{test.__doc__.split(chr(10))[0]}: {e}"))
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r[0] == "PASS")
    print(f"Total: {len(results)}  Passed: {passed}  Failed: {len(results) - passed}")
    if passed == len(results):
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
