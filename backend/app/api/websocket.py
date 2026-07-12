"""
WebSocket 端点

- ws /api/ws/execution/{execution_id} — 实时推送执行日志和状态

消息格式：{"type": "step_log"|"status_change"|"error", "data": {...}}
"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])

# 存储活跃连接：execution_id → [WebSocket, ...]
_active_connections: dict[str, list[WebSocket]] = {}


def get_active_connections(execution_id: str) -> list[WebSocket]:
    """获取或创建某个执行 ID 的连接列表"""
    if execution_id not in _active_connections:
        _active_connections[execution_id] = []
    return _active_connections[execution_id]


async def broadcast_to_execution(execution_id: str, message: dict):
    """向所有监听某个执行 ID 的客户端广播消息"""
    connections = _active_connections.get(execution_id, [])
    dead = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)


async def broadcast_log(execution_id: str, log_entry: dict):
    """广播日志消息"""
    await broadcast_to_execution(execution_id, {
        "type": "step_log",
        "data": log_entry,
    })


async def broadcast_status(execution_id: str, status: str):
    """广播状态变更"""
    await broadcast_to_execution(execution_id, {
        "type": "status_change",
        "data": {"status": status},
    })


async def broadcast_error(execution_id: str, error: str):
    """广播错误消息"""
    await broadcast_to_execution(execution_id, {
        "type": "error",
        "data": {"error": error},
    })


@router.websocket("/ws/execution/{execution_id}")
async def execution_websocket(ws: WebSocket, execution_id: str):
    """
    WebSocket 连接：实时获取执行日志和状态推送

    连接后自动接收 status_change 和 step_log 消息。
    """
    await ws.accept()
    connections = get_active_connections(execution_id)
    connections.append(ws)

    try:
        # 保持连接，等待客户端关闭
        while True:
            # 接收客户端心跳（ping/pong）
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            connections.remove(ws)
        except ValueError:
            pass
