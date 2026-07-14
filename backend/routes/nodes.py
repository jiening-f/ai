"""节点配置 API — 读取/保存 nodes.json，启停流程"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import random

from backend.engine.process_manager import (
    start_engine,
    stop_engine,
    get_engine_status,
)

router = APIRouter()

NODES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nodes.json"
)

# 当前节点引擎的 execution_id（简化方案，实际应由 DB 管理）
_NODE_EXECUTION_ID: Optional[int] = None


# ══ 请求模型 ══════════════════════════════════

class FeatureNodeModel(BaseModel):
    id: str
    map_id: str = ""
    detect_type: str = "text"       # text / image / key
    detect_value: str = ""
    on_match: str = "continue"      # continue / restart
    on_mismatch: str = "continue"
    enabled: bool = True


class MapConfigModel(BaseModel):
    id: str
    name: str
    enabled: bool = True
    features: List[FeatureNodeModel] = []


class NodeFlowModel(BaseModel):
    maps: List[MapConfigModel] = []
    loop_enabled: bool = True
    max_loops: int = 0


# ══ 序列化 ↔ 数据模型 ══════════════════════════

def _dumps_nodes(flow: NodeFlowModel) -> dict:
    """模型 → JSON 数据"""
    return {
        "maps": [
            {
                "id": m.id,
                "name": m.name,
                "enabled": m.enabled,
                "features": [
                    {
                        "id": f.id,
                        "map_id": f.map_id,
                        "detect_type": f.detect_type,
                        "detect_value": f.detect_value,
                        "on_match": f.on_match,
                        "on_mismatch": f.on_mismatch,
                        "enabled": f.enabled,
                    }
                    for f in m.features
                ],
            }
            for m in flow.maps
        ],
        "loop_enabled": flow.loop_enabled,
        "max_loops": flow.max_loops,
    }


def _format_flow_data(data: NodeFlowModel) -> dict:
    """将 NodeFlowModel 转为 engine_process 可接受的 flow 配置"""
    return _dumps_nodes(data)


# ══ 路由 ═══════════════════════════════════════

@router.get("/nodes")
def get_nodes():
    """读取 nodes.json 并返回"""
    if not os.path.isfile(NODES_FILE):
        return {"maps": [], "loop_enabled": True, "max_loops": 0}
    try:
        with open(NODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"读取节点配置失败: {e}")


@router.post("/nodes")
def save_nodes(data: NodeFlowModel):
    """保存 nodes.json"""
    try:
        payload = _dumps_nodes(data)
        os.makedirs(os.path.dirname(NODES_FILE), exist_ok=True)
        with open(NODES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "message": "节点配置已保存"}
    except Exception as e:
        raise HTTPException(500, f"保存节点配置失败: {e}")


@router.post("/nodes/run")
def run_nodes(data: NodeFlowModel):
    """启动节点流程 — 通过 EngineProcessManager 启动独立子进程"""
    global _NODE_EXECUTION_ID

    # 检查是否已在运行
    if _NODE_EXECUTION_ID is not None:
        existing = get_engine_status(_NODE_EXECUTION_ID)
        if existing and existing.get("alive"):
            raise HTTPException(409, "节点流程已在运行中")

    flow_data = _format_flow_data(data)
    execution_id = random.randint(10000, 99999)
    _NODE_EXECUTION_ID = execution_id

    config = {
        "flow": flow_data,
    }

    result = start_engine(
        execution_id=execution_id,
        mode="node",
        config=config,
    )

    if result["status"] == "error":
        _NODE_EXECUTION_ID = None
        raise HTTPException(500, result["message"])

    return {
        "status": "ok",
        "message": "流程已启动",
        "execution_id": execution_id,
        "loop_enabled": data.loop_enabled,
        "max_loops": data.max_loops,
    }


@router.post("/nodes/stop")
def stop_nodes():
    """停止节点流程"""
    global _NODE_EXECUTION_ID
    if _NODE_EXECUTION_ID is None:
        return {"status": "ok", "message": "没有正在运行的节点流程"}

    result = stop_engine(_NODE_EXECUTION_ID)
    _NODE_EXECUTION_ID = None
    return {"status": "ok", "message": result["message"]}
