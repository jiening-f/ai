"""节点配置 API — 读取/保存 nodes.json，启停流程"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json, os, threading

from engine.node_engine import (
    NodeEngine, NodeFlow, MapConfig, FeatureNode,
    DetectType, Decision
)

router = APIRouter()

NODES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nodes.json"
)

# 全局引擎实例（线程安全保护）
_engine = NodeEngine()
_run_thread: Optional[threading.Thread] = None
_nodes_lock = threading.Lock()


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


def _parse_nodes(data: dict) -> NodeFlow:
    """JSON 数据 → 领域模型 NodeFlow"""
    flow = NodeFlow(
        loop_enabled=data.get("loop_enabled", True),
        max_loops=data.get("max_loops", 0),
    )
    for m_data in data.get("maps", []):
        if not isinstance(m_data, dict):
            continue
        features = []
        for f_data in m_data.get("features", []):
            if not isinstance(f_data, dict):
                continue
            try:
                dt = DetectType(f_data.get("detect_type", "text"))
            except ValueError:
                dt = DetectType.TEXT
            try:
                om = Decision(f_data.get("on_match", "continue"))
            except ValueError:
                om = Decision.CONTINUE
            try:
                omm = Decision(f_data.get("on_mismatch", "continue"))
            except ValueError:
                omm = Decision.CONTINUE

            features.append(FeatureNode(
                id=f_data.get("id", ""),
                map_id=f_data.get("map_id", m_data.get("id", "")),
                detect_type=dt,
                detect_value=f_data.get("detect_value", ""),
                on_match=om,
                on_mismatch=omm,
                enabled=f_data.get("enabled", True),
            ))
        flow.maps.append(MapConfig(
            id=m_data.get("id", ""),
            name=m_data.get("name", ""),
            enabled=m_data.get("enabled", True),
            features=features,
        ))
    return flow


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
    """启动节点流程（线程安全）"""
    global _engine, _run_thread

    with _nodes_lock:
        if _run_thread and _run_thread.is_alive():
            raise HTTPException(409, "节点流程已在运行中")

        flow = _parse_nodes(_dumps_nodes(data))

        log_msgs = []

        def on_log(msg: str):
            log_msgs.append(msg)

        _engine = NodeEngine()
        _run_thread = threading.Thread(target=_engine.run, args=(flow,), kwargs={"on_log": on_log})
        _run_thread.daemon = True
        _run_thread.start()

    return {"status": "ok", "message": "流程已启动", "loop_enabled": flow.loop_enabled, "max_loops": flow.max_loops}


@router.post("/nodes/stop")
def stop_nodes():
    """停止节点流程（线程安全）"""
    global _engine, _run_thread
    with _nodes_lock:
        _engine.stop()
        if _run_thread:
            _run_thread.join(timeout=3)
            _run_thread = None
    return {"status": "ok", "message": "流程已停止"}
