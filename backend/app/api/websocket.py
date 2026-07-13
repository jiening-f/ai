"""WebSocket 端点 — 实时推送执行状态和步骤日志"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db import AsyncSessionLocal
from database.models import Execution, ExecutionStep

router = APIRouter()

# {execution_id: [WebSocket, ...]}
_connections: dict[int, list[WebSocket]] = {}
# R2 修复: 保存主事件循环引用，供后台线程使用 run_coroutine_threadsafe
_main_loop: asyncio.AbstractEventLoop = None


def _status_msg(ex: Execution) -> dict:
    return {
        "type": "status_change",
        "data": {
            "execution_id": ex.id, "preset_id": ex.preset_id,
            "status": ex.status,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
            "duration_ms": ex.duration_ms, "error_message": ex.error_message,
            "timestamp": datetime.now().isoformat(),
        },
    }


def _step_msg(step: ExecutionStep) -> dict:
    return {
        "type": "step_log",
        "data": {
            "execution_id": step.execution_id, "step_id": step.id,
            "step_order": step.step_order, "node_id": step.node_id,
            "node_type": step.node_type, "status": step.status,
            "input_data": step.input_data, "output_data": step.output_data,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "finished_at": step.finished_at.isoformat() if step.finished_at else None,
            "timestamp": datetime.now().isoformat(),
        },
    }


# ── R2 修复: 异步广播函数（由同步代码通过 run_coroutine_threadsafe 调用）──

async def broadcast_status(execution_id: int, status_data: dict):
    """广播执行状态变更到所有 WebSocket 客户端"""
    conns = _connections.get(execution_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_json({
                "type": "execution_status",
                "data": status_data,
            })
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in conns:
            conns.remove(ws)


async def broadcast_step(execution_id: int, step_data: dict):
    """广播步骤日志到所有 WebSocket 客户端"""
    conns = _connections.get(execution_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_json({
                "type": "step_log",
                "data": step_data,
            })
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in conns:
            conns.remove(ws)


async def broadcast_log(execution_id: int, level: str, message: str):
    """广播日志消息到所有 WebSocket 客户端"""
    conns = _connections.get(execution_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_json({
                "type": "log",
                "data": {
                    "execution_id": execution_id,
                    "level": level,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                },
            })
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in conns:
            conns.remove(ws)


def get_ws_connections(execution_id: int) -> list[WebSocket]:
    """获取指定执行的 WebSocket 连接列表"""
    return _connections.get(execution_id, [])


# ── R2 修复: 线程安全广播调度器 ──

def schedule_broadcast_status(execution_id: int, status_data: dict):
    """从任何线程安全调度异步广播（使用 run_coroutine_threadsafe）"""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_status(execution_id, status_data), _main_loop
        )


def schedule_broadcast_step(execution_id: int, step_data: dict):
    """从任何线程安全调度异步广播"""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_step(execution_id, step_data), _main_loop
        )


def schedule_broadcast_log(execution_id: int, level: str, message: str):
    """从任何线程安全调度异步广播"""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_log(execution_id, level, message), _main_loop
        )


@router.websocket("/api/ws/execution/{execution_id}")
async def ws_execution(websocket: WebSocket, execution_id: int):
    """WebSocket: 实时推送执行状态和步骤日志

    连接建立时自动推送当前已有数据。
    客户端可发送 "ping" 收到 "pong"。
    """
    global _main_loop
    if _main_loop is None:
        _main_loop = asyncio.get_running_loop()

    await websocket.accept()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Execution).where(Execution.id == execution_id))
        ex = result.scalar_one_or_none()
        if ex:
            await websocket.send_json(_status_msg(ex))
            step_result = await db.execute(
                select(ExecutionStep)
                .where(ExecutionStep.execution_id == execution_id)
                .order_by(ExecutionStep.step_order)
            )
            for s in step_result.scalars().all():
                await websocket.send_json(_step_msg(s))

    _connections.setdefault(execution_id, []).append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        conns = _connections.get(execution_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            _connections.pop(execution_id, None)
