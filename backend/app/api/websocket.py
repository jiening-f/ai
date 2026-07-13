"""WebSocket 端点 — 实时推送执行状态和步骤日志

连接建立时自动推送当前已有数据，之后通过 EventBridge 实时接收引擎推送的事件。
客户端可发送 "ping" 收到 "pong"。
"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db import AsyncSessionLocal
from database.models import Execution, ExecutionStep
from app.api.events import event_bridge

router = APIRouter()


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


def _build_event(event_type: str, data: dict) -> dict:
    """构建标准事件消息"""
    return {"type": event_type, "data": {**data, "timestamp": datetime.now().isoformat()}}


@router.websocket("/api/ws/execution/{execution_id}")
async def ws_execution(websocket: WebSocket, execution_id: int):
    """WebSocket: 实时推送执行状态和步骤日志

    连接建立时自动推送当前已有数据。
    之后通过 EventBridge 实时接收引擎推送事件并转发。
    客户端可发送 "ping" 收到 "pong"。
    """
    await websocket.accept()

    # 注册事件循环（首次连接时）
    try:
        loop = asyncio.get_running_loop()
        event_bridge.set_loop(loop)
    except RuntimeError:
        pass

    # 发送当前已有数据
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

    # 订阅实时事件
    eq = event_bridge.subscribe(execution_id)

    async def event_pusher():
        """后台任务：从事件桥读取事件并推送到 WebSocket"""
        while True:
            try:
                event = await eq.get()
                await websocket.send_json(event)
            except Exception:
                break

    push_task = asyncio.create_task(event_pusher())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        try:
            await push_task
        except (asyncio.CancelledError, Exception):
            pass
        event_bridge.unsubscribe(execution_id, eq)
