"""测试 engine/executor/context.py — ExecutionContext 变量/日志/统计/状态"""

import pytest
import time

from engine.executor.context import ExecutionContext


# ═══════════════════════════════════════════════════════════════
# 变量读写
# ═══════════════════════════════════════════════════════════════

class TestVariables:
    def test_set_and_get_var(self):
        ctx = ExecutionContext()
        ctx.set_var("key1", "value1")
        assert ctx.get_var("key1") == "value1"

    def test_get_var_default(self):
        ctx = ExecutionContext()
        assert ctx.get_var("nonexistent") is None
        assert ctx.get_var("nonexistent", "default") == "default"

    def test_get_all_variables(self):
        ctx = ExecutionContext()
        ctx.set_var("a", 1)
        ctx.set_var("b", 2)
        all_vars = ctx.get_all_variables()
        assert all_vars == {"a": 1, "b": 2}
        # 返回的是拷贝
        all_vars["c"] = 3
        assert ctx.get_var("c") is None

    def test_node_output(self):
        ctx = ExecutionContext()
        ctx.set_node_output("node1", {"result": "ok"})
        assert ctx.get_node_output("node1") == {"result": "ok"}
        assert ctx.get_node_output("node2") is None


# ═══════════════════════════════════════════════════════════════
# 截图缓存
# ═══════════════════════════════════════════════════════════════

class TestScreenshots:
    def test_cache_and_get(self):
        ctx = ExecutionContext()
        fake_img = object()
        ctx.cache_screenshot("screen1", fake_img)
        assert ctx.get_screenshot("screen1") is fake_img

    def test_clear_screenshots(self):
        ctx = ExecutionContext()
        ctx.cache_screenshot("s1", "img1")
        ctx.cache_screenshot("s2", "img2")
        ctx.clear_screenshots()
        assert ctx.get_screenshot("s1") is None
        assert ctx.get_screenshot("s2") is None

    def test_get_missing_screenshot(self):
        ctx = ExecutionContext()
        assert ctx.get_screenshot("missing") is None


# ═══════════════════════════════════════════════════════════════
# 日志收集
# ═══════════════════════════════════════════════════════════════

class TestLogging:
    def test_info_log(self):
        ctx = ExecutionContext()
        entry = ctx.info("test message", "n1", {"extra": "data"})
        assert entry["level"] == "INFO"
        assert entry["message"] == "test message"
        assert entry["node_id"] == "n1"
        assert entry["data"] == {"extra": "data"}
        assert "timestamp" in entry

    def test_warn_log(self):
        ctx = ExecutionContext()
        entry = ctx.warn("warning!")
        assert entry["level"] == "WARN"

    def test_error_log(self):
        ctx = ExecutionContext()
        entry = ctx.error("fatal!")
        assert entry["level"] == "ERROR"

    def test_get_logs(self):
        ctx = ExecutionContext()
        ctx.info("a")
        ctx.info("b")
        ctx.error("c")
        assert len(ctx.get_logs()) == 3

    def test_get_recent_logs(self):
        ctx = ExecutionContext()
        for i in range(100):
            ctx.info(f"msg_{i}")
        recent = ctx.get_recent_logs(5)
        assert len(recent) == 5
        assert recent[-1]["message"] == "msg_99"

    def test_get_recent_logs_empty(self):
        ctx = ExecutionContext()
        assert ctx.get_recent_logs(10) == []

    def test_log_timestamp_is_float(self):
        ctx = ExecutionContext()
        entry = ctx.info("msg")
        assert isinstance(entry["timestamp"], float)

    def test_log_defaults(self):
        """测试 log 方法的默认值"""
        ctx = ExecutionContext()
        entry = ctx.log("INFO", "msg")
        assert entry["node_id"] == ""
        assert entry["data"] is None


# ═══════════════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════════════

class TestStats:
    def test_initial_stats(self):
        ctx = ExecutionContext()
        stats = ctx.stats
        assert stats["executed_count"] == 0
        assert stats["success_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["start_time"] is None
        assert stats["current_node"] is None

    def test_mark_start(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        stats = ctx.stats
        assert stats["start_time"] is not None
        assert stats["executed_count"] == 0

    def test_mark_executed_success(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        ctx.mark_executed("n1", True)
        stats = ctx.stats
        assert stats["executed_count"] == 1
        assert stats["success_count"] == 1
        assert stats["failed_count"] == 0
        assert stats["current_node"] == "n1"

    def test_mark_executed_failed(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        ctx.mark_executed("n1", False)
        stats = ctx.stats
        assert stats["executed_count"] == 1
        assert stats["success_count"] == 0
        assert stats["failed_count"] == 1

    def test_mark_current_node(self):
        ctx = ExecutionContext()
        ctx.mark_current_node("some_node")
        assert ctx.stats["current_node"] == "some_node"
        ctx.mark_current_node(None)
        assert ctx.stats["current_node"] is None

    def test_elapsed_time(self):
        ctx = ExecutionContext()
        ctx.mark_start()
        time.sleep(0.01)
        stats = ctx.stats
        assert stats["elapsed_ms"] > 0

    def test_mark_start_resets_counters(self):
        ctx = ExecutionContext()
        ctx.mark_executed("n1", True)
        ctx.mark_executed("n2", False)
        ctx.mark_start()  # 重置
        assert ctx.stats["executed_count"] == 0
        assert ctx.stats["success_count"] == 0
        assert ctx.stats["failed_count"] == 0


# ═══════════════════════════════════════════════════════════════
# 状态控制
# ═══════════════════════════════════════════════════════════════

class TestStateControl:
    def test_initial_state(self):
        ctx = ExecutionContext()
        assert ctx.running is True
        assert ctx.paused is False
        assert ctx.stopped is False
        assert ctx.step_mode is False
        assert ctx.is_active() is True

    def test_pause_resume(self):
        ctx = ExecutionContext()
        ctx.pause()
        assert ctx.paused is True
        ctx.resume()
        assert ctx.paused is False

    def test_stop(self):
        ctx = ExecutionContext()
        ctx.stop()
        assert ctx.stopped is True
        assert ctx.running is False
        assert ctx.is_active() is False

    def test_enable_step_mode(self):
        ctx = ExecutionContext()
        ctx.enable_step_mode()
        assert ctx.step_mode is True
        assert ctx.paused is True  # 单步模式开始时应暂停

    def test_step_once(self):
        ctx = ExecutionContext()
        ctx.enable_step_mode()
        ctx.step_once()
        assert ctx.paused is False  # 放行一个节点

    def test_is_active(self):
        ctx = ExecutionContext()
        assert ctx.is_active() is True
        ctx.running = False
        assert ctx.is_active() is False
        ctx.running = True
        ctx.stopped = False
        assert ctx.is_active() is True
        ctx.stopped = True
        assert ctx.is_active() is False


# ═══════════════════════════════════════════════════════════════
# 综合测试
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_workflow(self):
        """模拟一次完整执行上下文的生命周期"""
        ctx = ExecutionContext()
        ctx.mark_start()

        # 节点 1 执行
        ctx.set_var("input", "hello")
        ctx.mark_current_node("node_1")
        ctx.info("开始处理", "node_1")
        ctx.mark_executed("node_1", True)

        # 节点 2 执行
        val = ctx.get_var("input")
        ctx.set_var("output", val.upper())
        ctx.mark_current_node("node_2")
        ctx.info("处理完成", "node_2")
        ctx.mark_executed("node_2", True)

        # 验证
        assert ctx.stats["executed_count"] == 2
        assert ctx.stats["success_count"] == 2
        assert ctx.stats["failed_count"] == 0
        assert ctx.get_var("output") == "HELLO"
        assert len(ctx.get_logs()) == 2

        # 停止
        ctx.stop()
        assert ctx.is_active() is False
