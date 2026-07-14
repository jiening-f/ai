"""WebSocket 端点 — 实时推送执行状态、步骤日志、引擎通信"""
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update

from app.db import AsyncSessionLocal
from database.models import Execution, ExecutionStep
from backend.engine.process_manager import update_heartbeat, update_status

router = APIRouter()

# ── 前端连接池 ──
# {execution_id: [WebSocket, ...]}
_connections: dict[int, list[WebSocket]] = {}

# ── 引擎连接池 ──
# {execution_id: WebSocket}
_engine_connections: dict[int, WebSocket] = {}


# ══ 内部辅助 ══════════════════════════════════════

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


async def broadcast_to_execution(execution_id: int, message: dict) -> None:
    """向指定 execution 的所有前端客户端广播消息"""
    conns = _connections.get(execution_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            conns.remove(ws)
        except ValueError:
            pass


async def _sync_status_to_db(execution_id: int, status: str, error_message: str = "") -> None:
    """将引擎状态变更同步到数据库"""
    async with AsyncSessionLocal() as db:
        now = datetime.now()
        update_data = {"status": status, "updated_at": now}
        if status == "running":
            update_data["started_at"] = now
        elif status in ("completed", "error", "stopped", "cancelled"):
            update_data["finished_at"] = now
            # 计算耗时
            stmt = select(Execution.started_at).where(Execution.id == execution_id)
            result = await db.execute(stmt)
            started_at = result.scalar_one_or_none()
            if started_at:
                duration = (now - started_at).total_seconds() * 1000
                update_data["duration_ms"] = int(duration)

        if error_message:
            update_data["error_message"] = error_message

        stmt = (
            update(Execution)
            .where(Execution.id == execution_id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.commit()


# ══ 前端 WebSocket ════════════════════════════════

@router.websocket("/api/ws/execution/{execution_id}")
async def ws_execution(websocket: WebSocket, execution_id: int):
    """WebSocket: 实时推送执行状态和步骤日志给前端

    连接建立时自动推送当前已有数据。
    客户端可发送 "ping" 收到 "pong"。
    支持控制指令：stop / pause / resume → 转发给引擎子进程。
    """
    await websocket.accept()

    # 推送已有数据
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
            else:
                # 尝试解析为控制指令 → 转发给引擎
                import json as _json
                try:
                    cmd = _json.loads(data)
                    cmd_type = cmd.get("type", "")
                    if cmd_type in ("stop", "pause", "resume"):
                        engine_ws = _engine_connections.get(execution_id)
                        if engine_ws:
                            try:
                                await engine_ws.send_text(data)
                            except Exception:
                                await websocket.send_json({
                                    "type": "error",
                                    "data": {"message": "引擎连接不可用"},
                                })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "data": {"message": "引擎未连接"},
                            })
                except (_json.JSONDecodeError, Exception):
                    pass  # 忽略无法解析的消息
    except WebSocketDisconnect:
        pass
    finally:
        conns = _connections.get(execution_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            _connections.pop(execution_id, None)


# ══ 引擎 WebSocket ════════════════════════════════

@router.websocket("/api/ws/engine/{execution_id}")
async def ws_engine(websocket: WebSocket, execution_id: int):
    """WebSocket: 引擎子进程专用连接

    引擎连接后：
      - 引擎消息自动广播到对应 execution 的前端客户端
      - 引擎状态变更自动同步到数据库
      - 心跳更新由 ProcessManager 跟踪

    消息类型：
      - engine_hello: 身份认证
      - heartbeat:     心跳
      - log:           日志行
      - step_log:      步骤日志
      - status_change: 状态变更
    """
    await websocket.accept()
    _engine_connections[execution_id] = websocket

    try:
        while True:
            raw = await websocket.receive_text()
            import json as _json
            try:
                data = _json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "engine_hello":
                    # 首次连接打招呼
                    update_status(execution_id, "connected")

                elif msg_type == "heartbeat":
                    # 更新心跳时间戳
                    update_heartbeat(execution_id)

                elif msg_type == "log":
                    # 日志行 → 广播给前端
                    await broadcast_to_execution(execution_id, data)

                elif msg_type == "step_log":
                    # 步骤日志 → 广播给前端
                    await broadcast_to_execution(execution_id, data)

                elif msg_type == "status_change":
                    status_data = data.get("data", {})
                    status = status_data.get("status", "")
                    error_msg = status_data.get("error_message", "")

                    # 更新 ProcessManager 状态
                    update_status(execution_id, status)

                    # 同步到数据库
                    await _sync_status_to_db(execution_id, status, error_msg)

                    # 广播给前端
                    await broadcast_to_execution(execution_id, data)

            except (_json.JSONDecodeError, Exception) as exc:
                print(f"[ws_engine] 解析引擎消息失败: {exc}")

    except WebSocketDisconnect:
        pass
    finally:
        # 清理连接记录
        if _engine_connections.get(execution_id) is websocket:
            _engine_connections.pop(execution_id, None)
        # 通知前端引擎断开
        await broadcast_to_execution(execution_id, {
            "type": "status_change",
            "data": {
                "execution_id": execution_id,
                "status": "disconnected",
                "timestamp": datetime.now().isoformat(),
            },
        })
