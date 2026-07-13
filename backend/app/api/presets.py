"""Presets 预设管理 API — CRUD + 执行控制（execute/stop/pause/resume/step）

执行引擎使用 backend/engine/engine.py 的 ScriptEngine（同步线程模型）。
通过 threading.Event 和运行状态字典实现启停控制。
通过 EventBridge 向 WebSocket 推送实时事件。
"""
import json, threading, sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db, DB_PATH
from database.models import Preset, Execution, ExecutionStep
from app.schemas.preset import (
    PresetCreate, PresetUpdate, PresetResponse, PresetDetailResponse,
)
from app.api import success, api_error, get_or_404
from app.api.events import event_bridge
from core.constants import _flog

router = APIRouter(prefix="/presets", tags=["Presets"])

# {preset_id: {"engine": ScriptEngine, "thread": Thread, "execution_id": int}}
_running: dict[int, dict] = {}


# ─── CRUD ───────────────────────────────────────

@router.get("")
async def list_presets(
    game_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """预设列表，支持按 game_id 筛选"""
    stmt = select(Preset).order_by(Preset.updated_at.desc())
    if game_id is not None:
        stmt = stmt.where(Preset.game_id == game_id)
    result = await db.execute(stmt)
    return success([PresetResponse.model_validate(p).model_dump(mode="json")
                     for p in result.scalars().all()])


@router.post("", status_code=201)
async def create_preset(body: PresetCreate, db: AsyncSession = Depends(get_db)):
    """创建预设"""
    preset = Preset(game_id=body.game_id, name=body.name,
                    description=body.description, flow_data=body.flow_data,
                    is_active=body.is_active)
    db.add(preset)
    await db.flush()
    await db.refresh(preset)
    return success(PresetDetailResponse.model_validate(preset).model_dump(mode="json"))


@router.get("/{preset_id}")
async def get_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """预设详情（含 flow_data）"""
    preset = await get_or_404(Preset, preset_id, db)
    return success(PresetDetailResponse.model_validate(preset).model_dump(mode="json"))


@router.put("/{preset_id}")
async def update_preset(preset_id: int, body: PresetUpdate, db: AsyncSession = Depends(get_db)):
    """更新预设"""
    preset = await get_or_404(Preset, preset_id, db)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(preset, k, v)
    preset.updated_at = datetime.now()
    await db.flush()
    await db.refresh(preset)
    return success(PresetDetailResponse.model_validate(preset).model_dump(mode="json"))


@router.delete("/{preset_id}")
async def delete_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """删除预设，同时停止正在运行的引擎"""
    preset = await get_or_404(Preset, preset_id, db)
    state = _running.pop(preset_id, None)
    if state and state.get("engine"):
        state["engine"].stop()
    await db.delete(preset)
    await db.flush()
    return success({"deleted": True, "id": preset_id})


# ─── 执行控制 ───────────────────────────────────

@router.post("/{preset_id}/execute")
async def execute_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """执行预设 — 后台线程启动 ScriptEngine"""
    preset = await get_or_404(Preset, preset_id, db)

    # 检查是否已在执行
    state = _running.get(preset_id)
    if state and state.get("thread") and state["thread"].is_alive():
        raise api_error("该预设正在执行中，请先停止", 409)

    # 解析 flow_data
    try:
        flow = json.loads(preset.flow_data) if isinstance(preset.flow_data, str) else preset.flow_data
    except (json.JSONDecodeError, TypeError):
        flow = {}

    steps = flow.get("steps", [])
    max_runs = flow.get("max_runs", 0)
    round_interval = flow.get("round_interval", 0)
    chain = flow.get("chain", True)

    # 创建执行记录（显式设置 started_at）
    now = datetime.now()
    execution = Execution(preset_id=preset_id, status="running", started_at=now)
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # 创建步骤记录
    for idx, step in enumerate(steps):
        db.add(ExecutionStep(
            execution_id=execution.id, step_order=idx + 1,
            node_id=step.get("id", f"step_{idx}"),
            node_type=step.get("action_type", step.get("condition_type", "")),
            status="pending",
            input_data=json.dumps(step, ensure_ascii=False),
        ))
    await db.flush()

    eid = execution.id  # 捕获供回调使用

    # 后台执行回调 — 使用 DB_PATH 避免四层 os.path.dirname（P1#2 修复）
    def _on_done():
        try:
            conn = sqlite3.connect(DB_PATH)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 通过 monitor() 方法获取引擎状态（P1#4 修复：不直接访问 _stop_ev）
            eng = _running.get(preset_id, {}).get("engine")
            if eng and eng.is_stopped():
                status = "stopped"
            elif eng and eng.monitor().get("error"):
                status = "error"
            else:
                status = "completed"
            error_msg = eng.monitor().get("error") or None if eng else None
            duration = int((datetime.now() - execution.started_at).total_seconds() * 1000) \
                if execution.started_at else None
            conn.execute(
                "UPDATE executions SET status=?, finished_at=?, duration_ms=?, error_message=? WHERE id=?",
                (status, now_str, duration, error_msg, eid),
            )
            conn.commit()
            conn.close()

            # 向 WebSocket 推送最终状态
            event_bridge.push(eid, {
                "type": "status_change",
                "data": {
                    "execution_id": eid, "preset_id": preset_id,
                    "status": status, "error_message": error_msg,
                    "finished_at": now_str, "duration_ms": duration,
                    "timestamp": datetime.now().isoformat(),
                },
            })
        except Exception as e:
            _flog(f"执行 {eid} 完成回调异常: {e}")

    def _bg_run():
        from engine.engine import ScriptEngine
        eng = ScriptEngine()
        eng.running = True
        eng._stop_ev.clear()

        # 更新注册的引擎引用
        state = _running.get(preset_id)
        if state:
            state["engine"] = eng

        def on_step(step_order: int, total: int, round_num: int, status: str, message: str):
            """结构化步骤回调 — 推送步骤事件到 WebSocket"""
            event_bridge.push(eid, {
                "type": "step_log",
                "data": {
                    "execution_id": eid,
                    "step_order": step_order,
                    "total": total,
                    "round": round_num,
                    "node_type": "",
                    "status": status,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                },
            })

        try:
            eng.run(
                {"name": preset.name, "steps": steps,
                 "max_runs": max_runs, "round_interval": round_interval, "chain": chain},
                chain=chain, on_step=on_step, on_done=_on_done,
            )
        except Exception as e:
            _flog(f"预设 {preset.name} (id={preset_id}) 执行异常: {e}")
        finally:
            _running.pop(preset_id, None)

    # P1#3 修复：启动线程前预先注册完整 state，避免竞态条件
    t = threading.Thread(target=_bg_run, daemon=True)
    _running[preset_id] = {"engine": None, "thread": t, "execution_id": eid}
    t.start()

    return success({"execution_id": eid, "status": "running",
                     "message": f"预设 «{preset.name}» 已启动"})


@router.post("/{preset_id}/stop")
async def stop_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """停止执行"""
    state = _running.get(preset_id)
    if not state or not state.get("thread") or not state["thread"].is_alive():
        raise api_error("该预设未在运行", 409)

    eng = state.get("engine")
    if eng:
        eng.stop()

    # 更新执行记录状态
    eid = state.get("execution_id")
    if eid:
        result = await db.execute(select(Execution).where(Execution.id == eid))
        ex = result.scalar_one_or_none()
        if ex and ex.status == "running":
            ex.status = "stopped"
            ex.finished_at = datetime.now()
            if ex.started_at:
                ex.duration_ms = int((datetime.now() - ex.started_at).total_seconds() * 1000)
            await db.flush()

    return success({"stopped": True, "preset_id": preset_id})


@router.post("/{preset_id}/pause")
async def pause_preset(preset_id: int):
    """暂停 — 当前轮完成后自动停止"""
    state = _running.get(preset_id)
    if not state or not state.get("thread") or not state["thread"].is_alive():
        raise api_error("该预设未在运行", 409)

    eng = state.get("engine")
    if eng:
        current_step = eng.monitor().get("step", 0)
        eng.stop_after = max(current_step, 1)
    return success({"paused": True, "preset_id": preset_id})


@router.post("/{preset_id}/resume")
async def resume_preset(preset_id: int):
    """恢复 — 清除暂停标记"""
    state = _running.get(preset_id)
    if not state or not state.get("thread") or not state["thread"].is_alive():
        raise api_error("该预设未在运行", 409)

    eng = state.get("engine")
    if eng:
        eng.stop_after = 0
    return success({"resumed": True, "preset_id": preset_id})


@router.post("/{preset_id}/step")
async def step_preset(preset_id: int):
    """单步执行 — 执行下一步后暂停"""
    state = _running.get(preset_id)
    if not state or not state.get("thread") or not state["thread"].is_alive():
        raise api_error("该预设未在运行", 409)

    eng = state.get("engine")
    if eng:
        current = eng.monitor().get("step", 0)
        eng.stop_after = current + 1 if current > 0 else 1
    return success({"step": True, "preset_id": preset_id})
