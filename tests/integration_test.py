"""集成测试 — 端到端验证 API / 引擎 / WebSocket / 跨模块兼容性

用法:
    PYTHONIOENCODING=utf-8 pytest tests/integration_test.py -v
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ_ROOT))

_results: list[dict] = []


def _record(name: str, passed: bool, detail: str = ""):
    _results.append({"name": name, "passed": passed, "detail": detail})


# ═══════════════════════════════════════════════════
# 第一部分: 引擎节点测试
# ═══════════════════════════════════════════════════


class TestEngineNodes:
    """验证 20 种节点类型"""

    def test_all_nodes_registered(self):
        """所有节点类型在注册表中"""
        from engine.nodes import NODE_REGISTRY
        expected = {
            "start", "end", "wait", "log", "condition", "loop",
            "key_press", "key_combo", "key_hold",
            "mouse_move", "mouse_click", "mouse_dblclick",
            "mouse_right", "mouse_drag", "mouse_scroll",
            "ocr_recognize", "template_match", "screenshot",
            "variable_set", "text_output",
        }
        actual = set(NODE_REGISTRY.keys())
        missing = expected - actual
        extra = actual - expected
        assert not missing, f"缺失节点类型: {missing}"
        _record("节点注册表完整", True, f"共{len(actual)}种节点")

    def test_all_nodes_instantiate_and_validate(self):
        """所有节点类型可实例化并通过 validate()"""
        from engine.nodes import NODE_REGISTRY, create_node

        configs = {
            "key_press": {"key": "a"},
            "key_combo": {"keys": ["ctrl", "c"]},
            "key_hold": {"key": "shift", "duration": 1.0},
            "mouse_move": {"x": 100, "y": 200},
            "mouse_click": {"x": 100, "y": 200},
            "mouse_dblclick": {},
            "mouse_right": {},
            "mouse_drag": {"from_x": 0, "from_y": 0, "to_x": 100, "to_y": 200},
            "mouse_scroll": {"direction": "down"},
            "ocr_recognize": {"expected_text": "test"},
            "template_match": {"template": "img.png", "confidence": 0.8},
            "screenshot": {"save_key": "test"},
            "variable_set": {"key": "x", "value": 42},
            "text_output": {"text": "hello"},
            "wait": {"duration": 0.1},
        }

        for name, cls in NODE_REGISTRY.items():
            cfg = configs.get(name, {})
            node = create_node(name, f"{name}_t1", cfg)
            assert node.validate(), f"{name}.validate() 返回 False"
        _record("节点实例化与校验", True)

    def test_node_execute_basic(self):
        """基本节点执行（start/wait/log/end）"""
        from engine.nodes import create_node
        from engine.executor.context import ExecutionContext

        ctx = ExecutionContext()
        ctx.mark_start()

        nodes = [
            create_node("start", "s"),
            create_node("wait", "w", {"duration": 0.01}),
            create_node("log", "l", {"message": "test"}),
            create_node("end", "e"),
        ]

        for n in nodes:
            r = asyncio.run(n.execute(ctx))
            ctx.mark_executed(n.node_id, r.status.value == "success")

        assert ctx.stats["executed_count"] == 4
        _record("基本节点执行", True)


class TestEngineRunner:
    """验证引擎执行器核心功能"""

    def test_basic_flow(self):
        """基本线性流程 start->wait->log->end"""
        from engine.nodes.flow import StartNode, EndNode, WaitNode, LogNode
        from engine.executor.runner import create_runner

        nodes = {
            "start": StartNode("start"),
            "wait": WaitNode("wait", {"duration": 0.05}),
            "log": LogNode("log", {"message": "hello"}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["wait"]
        nodes["wait"].next_nodes = ["log"]
        nodes["log"].next_nodes = ["end"]

        runner = create_runner(nodes, "start", with_logging=False)
        ctx = asyncio.run(runner.run())
        assert ctx.stats["executed_count"] == 4
        assert runner.state.value == "completed"
        _record("基本线性流程", True)

    def test_compound_flow_10plus_nodes(self):
        """复合流程: 14节点含条件+循环+视觉+键盘+鼠标+变量"""
        from engine.nodes import create_node
        from engine.executor.runner import ScriptRunner

        nodes = {
            "start": create_node("start", "start"),
            "shot": create_node("screenshot", "shot", {"save_key": "main"}),
            "ocr": create_node("ocr_recognize", "ocr", {"expected_text": "test"}),
            "tmpl": create_node("template_match", "tmpl",
                                {"template": "btn.png", "confidence": 0.8}),
            "check": create_node("condition", "check", {
                "condition": "True", "true_branch": "key_a", "false_branch": "move",
            }),
            "key_a": create_node("key_press", "key_a", {"key": "a"}),
            "combo": create_node("key_combo", "combo", {"keys": ["ctrl", "s"]}),
            "txt": create_node("text_output", "txt", {"text": "Hello"}),
            "var": create_node("variable_set", "var",
                               {"key": "counter", "value": 1}),
            "w": create_node("wait", "w", {"duration": 0.02}),
            "loop": create_node("loop", "loop", {
                "condition": 'vars.get("counter", 0) < 2',
                "loop_target": "key_a", "max_iterations": 3,
            }),
            "move": create_node("mouse_move", "move", {"x": 100, "y": 200}),
            "click": create_node("mouse_click", "click", {"x": 100, "y": 200}),
            "end": create_node("end", "end"),
        }
        nodes["start"].next_nodes = ["shot"]
        nodes["shot"].next_nodes = ["ocr"]
        nodes["ocr"].next_nodes = ["tmpl"]
        nodes["tmpl"].next_nodes = ["check"]
        nodes["check"].next_nodes = ["key_a", "move"]
        nodes["key_a"].next_nodes = ["combo"]
        nodes["combo"].next_nodes = ["txt"]
        nodes["txt"].next_nodes = ["var"]
        nodes["var"].next_nodes = ["w"]
        nodes["w"].next_nodes = ["loop"]
        nodes["loop"].next_nodes = ["end"]
        nodes["move"].next_nodes = ["click"]
        nodes["click"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start")
        ctx = asyncio.run(runner.run())

        assert runner.state.value == "completed"
        assert ctx.stats["executed_count"] >= 10
        assert ctx.stats["failed_count"] == 0
        _record("14节点复合流程", True,
                f"执行{ctx.stats['executed_count']}节点, 耗时{ctx.stats['elapsed_ms']}ms")

    def test_condition_branch(self):
        """条件分支"""
        from engine.nodes.flow import StartNode, EndNode, LogNode, ConditionNode
        from engine.executor.runner import ScriptRunner

        nodes = {
            "start": StartNode("start"),
            "check": ConditionNode("check", {
                "condition": "True", "true_branch": "path_a", "false_branch": "path_b",
            }),
            "path_a": LogNode("path_a", {"message": "A"}),
            "path_b": LogNode("path_b", {"message": "B"}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["check"]
        nodes["check"].next_nodes = ["path_a", "path_b"]
        nodes["path_a"].next_nodes = ["end"]
        nodes["path_b"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start")
        ctx = asyncio.run(runner.run())
        log_ids = [e["node_id"] for e in ctx.get_logs()]
        assert "path_a" in log_ids
        _record("条件分支", True)

    def test_loop_node(self):
        """循环节点"""
        from engine.nodes import create_node
        from engine.executor.runner import ScriptRunner

        nodes = {
            "start": create_node("start", "start"),
            "var": create_node("variable_set", "var", {"key": "count", "value": 0}),
            "loop": create_node("loop", "loop", {
                "condition": 'vars.get("count", 0) < 3',
                "loop_target": "inc", "max_iterations": 5,
            }),
            "inc": create_node("variable_set", "inc", {
                "key": "count", "expression": "vars.get('count',0)+1",
            }),
            "end": create_node("end", "end"),
        }
        nodes["start"].next_nodes = ["var"]
        nodes["var"].next_nodes = ["loop"]
        nodes["loop"].next_nodes = ["end"]
        nodes["inc"].next_nodes = ["loop"]

        runner = ScriptRunner(nodes, "start")
        ctx = asyncio.run(runner.run())
        assert runner.state.value == "completed"
        assert ctx.get_var("count", 0) >= 3
        _record("循环节点", True, f"count={ctx.get_var('count')}")

    def test_state_machine_pause_resume(self):
        """暂停/恢复"""
        from engine.nodes.flow import StartNode, EndNode, WaitNode
        from engine.executor.runner import create_runner

        nodes = {
            "start": StartNode("start"),
            "w1": WaitNode("w1", {"duration": 0.05}),
            "w2": WaitNode("w2", {"duration": 0.05}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["w1"]
        nodes["w1"].next_nodes = ["w2"]
        nodes["w2"].next_nodes = ["end"]

        runner = create_runner(nodes, "start", with_logging=False)

        async def run_with_pause():
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(0.02)
            await runner.pause()
            assert runner.state.value == "paused"
            await asyncio.sleep(0.1)
            assert runner.state.value == "paused"
            await runner.resume()
            assert runner.state.value == "running"
            return await task

        ctx = asyncio.run(run_with_pause())
        assert ctx.stats["executed_count"] >= 2
        _record("暂停恢复", True)

    def test_state_machine_stop(self):
        """停止"""
        from engine.nodes.flow import StartNode, EndNode, WaitNode
        from engine.executor.runner import create_runner

        nodes = {
            "start": StartNode("start"),
            "wait": WaitNode("wait", {"duration": 1.0}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["wait"]
        nodes["wait"].next_nodes = ["end"]

        runner = create_runner(nodes, "start", with_logging=False)

        async def run_with_stop():
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(0.02)
            await runner.stop()
            return await task

        ctx = asyncio.run(run_with_stop())
        assert runner.state.value == "stopped"
        _record("停止", True)

    def test_state_machine_step_mode(self):
        """单步模式上下文设置"""
        from engine.nodes.flow import StartNode, EndNode, LogNode
        from engine.executor.runner import ScriptRunner
        from engine.executor.context import ExecutionContext

        nodes = {
            "start": StartNode("start"),
            "log": LogNode("log", {"message": "step"}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["log"]
        nodes["log"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start")
        ctx = ExecutionContext()
        ctx.mark_start()
        ctx.enable_step_mode()
        assert ctx.step_mode is True
        ctx.step_once()
        assert ctx.paused is False
        runner._ctx = ctx
        assert runner._ctx.step_mode is True
        _record("单步模式", True)

    def test_error_node_triggers_error_state(self):
        """错误节点触发 error 状态"""
        from engine.nodes.base import BaseNode, NodeResult, NodeStatus
        from engine.nodes.flow import StartNode, EndNode
        from engine.executor.runner import ScriptRunner

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

        runner = ScriptRunner(nodes, "start", on_error="stop")
        ctx = asyncio.run(runner.run())
        assert runner.state.value == "error"
        errors = [l["message"] for l in ctx.get_logs() if l["level"] == "ERROR"]
        assert any("模拟节点错误" in m for m in errors)
        _record("错误触发error状态", True)

    def test_error_continue_strategy(self):
        """错误跳过策略 on_error=continue"""
        from engine.nodes.base import BaseNode, NodeResult, NodeStatus
        from engine.nodes.flow import StartNode, EndNode, LogNode
        from engine.executor.runner import ScriptRunner

        class FailNode(BaseNode):
            node_type = "fail"
            async def execute(self, ctx):
                raise ValueError("偶发错误")

        nodes = {
            "start": StartNode("start"),
            "bad": FailNode("bad"),
            "ok": LogNode("ok", {"message": "继续了"}),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["bad"]
        nodes["bad"].next_nodes = ["ok"]
        nodes["ok"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start", on_error="continue")
        ctx = asyncio.run(runner.run())
        assert runner.state.value == "completed"
        _record("错误跳过continue", True)

    def test_error_retry_strategy(self):
        """错误重试策略 on_error=retry 配置验证"""
        from engine.nodes.flow import StartNode, EndNode
        from engine.executor.runner import ScriptRunner

        nodes = {
            "start": StartNode("start"),
            "end": EndNode("end"),
        }
        nodes["start"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start", on_error="retry", max_retries=2)
        ctx = asyncio.run(runner.run())
        assert runner.state.value == "completed"
        _record("retry策略配置", True)

    def test_hook_system(self):
        """钩子系统"""
        from engine.nodes.flow import StartNode, EndNode
        from engine.executor.runner import ScriptRunner
        from engine.executor.hooks import HookSystem

        hooks = HookSystem()
        pre_cnt = [0]
        post_cnt = [0]

        @hooks.on_pre_execute
        def cp(node, ctx):
            pre_cnt[0] += 1

        @hooks.on_post_execute
        def cp2(node, ctx, result):
            post_cnt[0] += 1

        nodes = {"start": StartNode("start"), "end": EndNode("end")}
        nodes["start"].next_nodes = ["end"]

        runner = ScriptRunner(nodes, "start", hooks=hooks)
        asyncio.run(runner.run())
        assert pre_cnt[0] >= 2
        assert post_cnt[0] >= 2
        _record("钩子系统", True, f"pre={pre_cnt[0]} post={post_cnt[0]}")

    def test_variable_flow(self):
        """变量在节点间传递"""
        from engine.nodes.base import BaseNode, NodeResult, NodeStatus
        from engine.nodes.flow import StartNode, EndNode
        from engine.executor.runner import ScriptRunner

        class SetVarNode(BaseNode):
            node_type = "set_var"
            async def execute(self, ctx):
                ctx.set_var("k1", "v1")
                ctx.set_node_output(self.node_id, "out1")
                return NodeResult(status=NodeStatus.SUCCESS)

        class GetVarNode(BaseNode):
            node_type = "get_var"
            async def execute(self, ctx):
                assert ctx.get_var("k1") == "v1"
                assert ctx.get_node_output("setter") == "out1"
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

        runner = ScriptRunner(nodes, "start")
        asyncio.run(runner.run())
        assert runner.state.value == "completed"
        _record("变量传递", True)


# ═══════════════════════════════════════════════════
# 第二部分: 后端 API 测试 (真实服务器)
# ═══════════════════════════════════════════════════


class TestBackendAPI:
    """启动真实后端服务器进行端到端 API 测试"""

    @pytest.fixture(scope="class")
    def server_url(self):
        import subprocess
        import urllib.request

        server_script = str(_PROJ_ROOT / "backend" / "server.py")
        proc = subprocess.Popen(
            [sys.executable, server_script],
            cwd=str(_PROJ_ROOT / "backend"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        base_url = "http://127.0.0.1:8765"
        for _ in range(20):
            try:
                urllib.request.urlopen(f"{base_url}/docs", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            proc.terminate()
            pytest.skip("服务器启动超时")
        yield base_url
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _get(self, url, path):
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.urlopen(f"{url}{path}", timeout=5)
            return req.status, json.loads(req.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, {}

    def test_health_check(self, server_url):
        """API 服务可访问"""
        import urllib.request
        resp = urllib.request.urlopen(f"{server_url}/docs", timeout=5)
        assert resp.status == 200
        _record("API文档可访问", True)

    def test_openapi_json(self, server_url):
        """OpenAPI JSON 含全部路由组"""
        status, data = self._get(server_url, "/openapi.json")
        assert status == 200
        paths = list(data.get("paths", {}).keys())
        prefixes = {p.split("/")[2] for p in paths
                    if p.startswith("/api/") and len(p.split("/")) > 2}
        assert "presets" in prefixes
        _record("OpenAPI路由完整", True, f"路由组: {prefixes}")

    def test_presets_list(self, server_url):
        """预设列表 API"""
        status, data = self._get(server_url, "/api/presets")
        assert status == 200
        assert data["success"] is True
        _record("预设列表API", True)

    def test_presets_404(self, server_url):
        """不存在的预设返回 404"""
        status, _ = self._get(server_url, "/api/presets/99999")
        assert status == 404
        _record("预设404响应", True)

    def test_executions_list(self, server_url):
        """执行记录列表"""
        status, data = self._get(server_url, "/api/executions")
        assert status == 200
        assert data["success"] is True
        _record("执行记录列表API", True)

    def test_executions_404(self, server_url):
        """不存在的执行记录"""
        status, _ = self._get(server_url, "/api/executions/99999")
        assert status == 404
        _record("执行记录404响应", True)

    def test_plugins_list(self, server_url):
        """插件列表"""
        status, data = self._get(server_url, "/api/plugins")
        assert status == 200
        assert data["success"] is True
        _record("插件列表API", True)

    def test_settings_list(self, server_url):
        """设置列表"""
        status, data = self._get(server_url, "/api/settings")
        assert status == 200
        assert data["success"] is True
        _record("设置列表API", True)

    def test_games_list(self, server_url):
        """游戏列表"""
        status, data = self._get(server_url, "/api/games")
        assert status == 200
        assert data["success"] is True
        _record("游戏列表API", True)

    def test_unified_response_format(self, server_url):
        """统一响应格式 {success, data, error}"""
        paths = ["/api/presets", "/api/executions", "/api/plugins",
                 "/api/settings", "/api/games"]
        for path in paths:
            status, data = self._get(server_url, path)
            if status == 200:
                assert "success" in data, f"{path} 缺少 success"
                assert "data" in data, f"{path} 缺少 data"
                assert "error" in data, f"{path} 缺少 error"
        _record("统一响应格式", True)

    def test_nonexistent_route_404(self, server_url):
        """不存在的路由返回 404"""
        status, _ = self._get(server_url, "/api/nonexistent_xyz")
        assert status == 404
        _record("不存在路由404", True)


# ═══════════════════════════════════════════════════
# 第三部分: WebSocket 测试
# ═══════════════════════════════════════════════════


class TestWebSocket:
    """WebSocket 基础设施验证"""

    def test_websocket_route_registered(self):
        """WebSocket 路由在 server.py 中注册"""
        server_py = _PROJ_ROOT / "backend" / "server.py"
        content = server_py.read_text(encoding="utf-8")
        assert "ws_router" in content
        _record("WebSocket路由注册", True)

    def test_websocket_broadcast_functions(self):
        """WebSocket 广播函数正确定义"""
        ws_py = _PROJ_ROOT / "backend" / "app" / "api" / "websocket.py"
        content = ws_py.read_text(encoding="utf-8")
        assert "async def broadcast_status" in content
        assert "async def broadcast_step" in content
        assert "async def broadcast_log" in content
        # R2: 验证 run_coroutine_threadsafe 线程安全调度
        assert "schedule_broadcast_status" in content
        assert "run_coroutine_threadsafe" in content
        _record("WebSocket广播函数", True)


# ═══════════════════════════════════════════════════
# 第四部分: 跨模块兼容性测试
# ═══════════════════════════════════════════════════


class TestCrossModuleCompat:
    """跨模块兼容性验证"""

    def test_base_class_unified(self):
        """Base 类统一: backend/db 从 database/models 导入"""
        db_py = _PROJ_ROOT / "backend" / "app" / "db.py"
        content = db_py.read_text(encoding="utf-8")
        assert "from database.models import Base" in content
        _record("Base类统一", True)

    def test_api_routes_registered_in_server(self):
        """API 路由全部在 server.py 中注册"""
        server_py = _PROJ_ROOT / "backend" / "server.py"
        content = server_py.read_text(encoding="utf-8")
        for r in ["games_router", "presets_router", "executions_router",
                   "plugins_router", "settings_router", "ws_router"]:
            assert r in content, f"server.py 缺少: {r}"
        _record("API路由注册完整", True)

    def test_schemas_optional_fields(self):
        """Schemas 可选字段声明"""
        schema_py = _PROJ_ROOT / "backend" / "app" / "schemas" / "execution.py"
        content = schema_py.read_text(encoding="utf-8")
        assert "Optional" in content
        assert "started_at" in content
        _record("Schemas Optional字段", True)

    def test_node_registry_exports(self):
        """engine/nodes/__init__.py 正确导出所有节点"""
        from engine.nodes import (
            BaseNode, NodeResult, NodeStatus,
            StartNode, EndNode, WaitNode, LogNode, ConditionNode, LoopNode,
            KeyPressNode, KeyComboNode, KeyHoldNode,
            MouseMoveNode, MouseClickNode, MouseDblClickNode,
            MouseRightNode, MouseDragNode, MouseScrollNode,
            ScreenshotNode, OcrRecognizeNode, TemplateMatchNode,
            VariableSetNode, TextOutputNode,
            NODE_REGISTRY, create_node,
        )
        assert len(NODE_REGISTRY) >= 19
        _record("节点注册表导出完整", True)


# ═══════════════════════════════════════════════════
# 第五部分: 安全性测试
# ═══════════════════════════════════════════════════


class TestSecurity:
    """安全相关测试"""

    def test_no_hardcoded_secrets(self):
        """代码中无硬编码密钥/Token/密码"""
        import re

        patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["\'][^\'"]{8,}["\']',
             "硬编码凭据"),
        ]

        scan_dirs = ["backend", "engine", "database"]
        found = []

        for scan_dir in scan_dirs:
            dir_path = _PROJ_ROOT / scan_dir
            if not dir_path.exists():
                continue
            for root, _, files in os.walk(dir_path):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, encoding="utf-8") as fh:
                            content = fh.read()
                    except Exception:
                        continue
                    for pat, desc in patterns:
                        for m in re.findall(pat, content):
                            # 排除注释
                            for line in content.split("\n"):
                                if isinstance(m, str) and m in line:
                                    stripped = line.strip()
                                    if stripped.startswith("#") or stripped.startswith('"""'):
                                        continue
                                    if "test" in fpath.lower():
                                        continue
                                    found.append(f"{fpath}: {desc}")
                                    break

        assert not found, f"发现安全问题: {found}"
        _record("无硬编码凭据", True)

    def test_db_path_from_config(self):
        """数据库路径来自配置计算"""
        db_py = _PROJ_ROOT / "backend" / "app" / "db.py"
        content = db_py.read_text(encoding="utf-8")
        assert "_PROJ_ROOT" in content
        assert "DB_PATH" in content
        _record("数据库路径配置化", True)
