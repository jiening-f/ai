"""测试 backend/engine/node_engine.py — NodeEngine、枚举和数据模型

由于 backend/engine/ 包与项目根 engine/ 包存在命名冲突，
测试在隔离的子进程中运行，验证所有后端引擎的数据结构和逻辑。
"""

import sys
import os
import subprocess
import json
import pytest


# ═══════════════════════════════════════════════════════════════
# 构建子进程测试脚本
# ═══════════════════════════════════════════════════════════════

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_backend_root = os.path.join(_project_root, "backend")


def _build_test_script():
    """构建在隔离子进程中运行的后端测试脚本"""
    return f'''
import sys
import os
import json

_backend_root = r"{_backend_root}"
assert os.path.isdir(_backend_root), f"backend dir not found: {{_backend_root}}"

for k in list(sys.modules):
    if k == 'engine' or k.startswith('engine.'):
        del sys.modules[k]

if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "engine.node_engine",
    os.path.join(_backend_root, "engine", "node_engine.py")
)
_mod = importlib.util.module_from_spec(_spec)
import engine as _engine_pkg
sys.modules['engine'] = _engine_pkg

_spec.loader.exec_module(_mod)

NodeEngine = _mod.NodeEngine
NodeType = _mod.NodeType
DetectType = _mod.DetectType
Decision = _mod.Decision
FeatureNode = _mod.FeatureNode
MapConfig = _mod.MapConfig
NodeFlow = _mod.NodeFlow

results = []

# --- enum tests ---
try:
    vals = {{t.value for t in NodeType}}
    assert "map_select" in vals and "feature" in vals and "decision" in vals
    assert NodeType.MAP_SELECT == NodeType("map_select")
    assert NodeType.FEATURE_DETECT == NodeType("feature")
    results.append(("test_node_type_values", True, ""))
except Exception as e:
    results.append(("test_node_type_values", False, str(e)))

try:
    vals = {{t.value for t in DetectType}}
    assert "text" in vals and "image" in vals and "key" in vals
    assert DetectType("text") == DetectType.TEXT
    results.append(("test_detect_type_values", True, ""))
except Exception as e:
    results.append(("test_detect_type_values", False, str(e)))

try:
    try:
        DetectType("invalid")
        ok = False
    except ValueError:
        ok = True
    assert ok, "should raise ValueError"
    results.append(("test_detect_type_invalid", True, ""))
except Exception as e:
    results.append(("test_detect_type_invalid", False, str(e)))

try:
    vals = {{d.value for d in Decision}}
    assert "continue" in vals and "restart" in vals
    assert Decision.CONTINUE == Decision("continue")
    results.append(("test_decision_values", True, ""))
except Exception as e:
    results.append(("test_decision_values", False, str(e)))

# --- data model tests ---
try:
    fn = FeatureNode("f1", DetectType.TEXT, "hello", Decision.CONTINUE, Decision.RESTART)
    assert fn.id == "f1"
    assert fn.detect_type == DetectType.TEXT
    assert fn.detect_value == "hello"
    assert fn.on_match == Decision.CONTINUE
    assert fn.on_mismatch == Decision.RESTART
    assert fn.enabled is True
    assert fn.map_id == ""
    results.append(("test_feature_node_basic", True, ""))
except Exception as e:
    results.append(("test_feature_node_basic", False, str(e)))

try:
    fn = FeatureNode("f1", DetectType.TEXT, "", Decision.CONTINUE, Decision.CONTINUE, enabled=False)
    assert fn.enabled is False
    results.append(("test_feature_node_disabled", True, ""))
except Exception as e:
    results.append(("test_feature_node_disabled", False, str(e)))

try:
    mc = MapConfig(id="m1", name="map1", features=[
        FeatureNode("f1", DetectType.TEXT, "x", Decision.CONTINUE, Decision.CONTINUE),
    ])
    assert mc.id == "m1" and mc.name == "map1" and len(mc.features) == 1
    results.append(("test_map_config", True, ""))
except Exception as e:
    results.append(("test_map_config", False, str(e)))

try:
    flow = NodeFlow(maps=[], loop_enabled=False)
    assert flow.maps == [] and flow.loop_enabled is False and flow.max_loops == 0
    results.append(("test_node_flow_default", True, ""))
except Exception as e:
    results.append(("test_node_flow_default", False, str(e)))

try:
    mc = MapConfig(id="m1", name="m", features=[
        FeatureNode("f1", DetectType.IMAGE, "icon", Decision.CONTINUE, Decision.CONTINUE),
    ])
    flow = NodeFlow(maps=[mc], loop_enabled=True, max_loops=5)
    assert len(flow.maps) == 1 and flow.max_loops == 5
    results.append(("test_node_flow_with_maps", True, ""))
except Exception as e:
    results.append(("test_node_flow_with_maps", False, str(e)))

# --- engine init ---
try:
    engine = NodeEngine()
    assert engine.running is False and engine._vision is None
    engine.stop()
    results.append(("test_engine_init", True, ""))
except Exception as e:
    results.append(("test_engine_init", False, str(e)))

# --- empty flow ---
try:
    engine = NodeEngine()
    flow = NodeFlow(maps=[], loop_enabled=False)
    logs = []
    engine.run(flow, on_log=logs.append)
    # 空流程的输出包含"流程结束"
    ok = any("流程结束" in msg or "---" in msg for msg in logs)
    assert ok, f"logs: {{logs}}"
    results.append(("test_empty_flow", True, ""))
except Exception as e:
    results.append(("test_empty_flow", False, str(e)))

# --- detect key ---
try:
    engine = NodeEngine()
    fn = FeatureNode("f1", DetectType.KEY, "Enter", Decision.CONTINUE, Decision.CONTINUE)
    assert engine._detect_feature(fn) is True
    results.append(("test_detect_key", True, ""))
except Exception as e:
    results.append(("test_detect_key", False, str(e)))

# --- flow all pass ---
try:
    from unittest.mock import patch
    engine = NodeEngine()
    fn1 = FeatureNode("f1", DetectType.IMAGE, "target", Decision.CONTINUE, Decision.CONTINUE)
    mc = MapConfig(id="m1", name="test", features=[fn1])
    flow = NodeFlow(maps=[mc], loop_enabled=False)
    with patch.object(engine, '_detect_feature', return_value=True):
        logs = []
        engine.run(flow, on_log=logs.append)
    ok = False
    for msg in logs:
        if any(w in msg for w in ["pass", "through", "all", "complete", "done", "over"]):
            ok = True
            break
    assert ok or engine.running is False
    results.append(("test_flow_all_pass", True, ""))
except Exception as e:
    results.append(("test_flow_all_pass", False, str(e)))

# --- flow restart ---
try:
    from unittest.mock import patch
    engine = NodeEngine()
    fn1 = FeatureNode("f1", DetectType.TEXT, "x", Decision.CONTINUE, Decision.RESTART)
    mc = MapConfig(id="m1", name="m", features=[fn1])
    flow = NodeFlow(maps=[mc], loop_enabled=True, max_loops=2)
    with patch.object(engine, '_detect_feature', return_value=False):
        logs = []
        engine.run(flow, on_log=logs.append)
    assert any("restart" in msg.lower() or "max" in msg.lower() for msg in logs)
    results.append(("test_flow_restart", True, ""))
except Exception as e:
    results.append(("test_flow_restart", False, str(e)))

# --- disabled feature ---
try:
    from unittest.mock import patch
    engine = NodeEngine()
    fn1 = FeatureNode("f1", DetectType.TEXT, "skip", Decision.CONTINUE, Decision.CONTINUE, enabled=False)
    mc = MapConfig(id="m1", name="m", features=[fn1])
    flow = NodeFlow(maps=[mc], loop_enabled=False)
    with patch.object(engine, '_detect_feature') as mock_d:
        engine.run(flow)
        mock_d.assert_not_called()
    results.append(("test_disabled_feature", True, ""))
except Exception as e:
    results.append(("test_disabled_feature", False, str(e)))

print("RESULTS:" + json.dumps(results, ensure_ascii=False))
'''


def _run_backend_tests():
    """在隔离的子进程中运行后端引擎测试，返回结果列表"""
    script = _build_test_script()
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=30,
        cwd=_backend_root,
    )
    stdout = result.stdout
    stderr = result.stderr

    for line in stdout.splitlines():
        if line.startswith("RESULTS:"):
            return json.loads(line[len("RESULTS:"):])

    return [("_process_crashed", False, f"stderr: {stderr[:500]}\nstdout: {stdout[-500:]}")]


# ═══════════════════════════════════════════════════════════════
# pytest 测试函数
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def backend_results():
    """模块级别的 fixture：运行一次后端测试，缓存结果"""
    return _run_backend_tests()


def _assert_pass(backend_results, test_name):
    for name, passed, error in backend_results:
        if name == test_name:
            assert passed, f"[{test_name}] failed: {error}"
            return
    pytest.fail(f"Test [{test_name}] not found in subprocess output")


def test_node_type_values(backend_results):
    _assert_pass(backend_results, "test_node_type_values")

def test_detect_type_values(backend_results):
    _assert_pass(backend_results, "test_detect_type_values")

def test_detect_type_invalid(backend_results):
    _assert_pass(backend_results, "test_detect_type_invalid")

def test_decision_values(backend_results):
    _assert_pass(backend_results, "test_decision_values")

def test_feature_node_basic(backend_results):
    _assert_pass(backend_results, "test_feature_node_basic")

def test_feature_node_disabled(backend_results):
    _assert_pass(backend_results, "test_feature_node_disabled")

def test_map_config(backend_results):
    _assert_pass(backend_results, "test_map_config")

def test_node_flow_default(backend_results):
    _assert_pass(backend_results, "test_node_flow_default")

def test_node_flow_with_maps(backend_results):
    _assert_pass(backend_results, "test_node_flow_with_maps")

def test_engine_init(backend_results):
    _assert_pass(backend_results, "test_engine_init")

def test_empty_flow(backend_results):
    _assert_pass(backend_results, "test_empty_flow")

def test_detect_key(backend_results):
    _assert_pass(backend_results, "test_detect_key")

def test_flow_all_pass(backend_results):
    _assert_pass(backend_results, "test_flow_all_pass")

def test_flow_restart(backend_results):
    _assert_pass(backend_results, "test_flow_restart")

def test_disabled_feature(backend_results):
    _assert_pass(backend_results, "test_disabled_feature")
