"""pytest 共享 fixtures 和配置"""
import sys
import os

# 确保项目根目录在 Python 路径中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest
import asyncio


@pytest.fixture
def sample_node_config():
    """标准节点配置样例"""
    return {
        "node_id": "test_node_1",
        "config": {
            "duration": 1.0,
            "message": "test message",
            "condition": "True",
            "max_iterations": 10,
            "loop_target": "start",
        },
    }


@pytest.fixture
def async_runner():
    """提供统一的异步测试执行器"""

    def _run(coro):
        return asyncio.run(coro)

    return _run
