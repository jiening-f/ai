"""Presets 预设管理 API — CRUD + 执行控制（execute/stop/pause/resume/step）

支持双引擎自动检测:
- 旧引擎 backend/engine/engine.py:ScriptEngine（同步线程，steps 格式）
- 新引擎 engine/executor/runner.py:ScriptRunner（async 图遍历，nodes 格式）
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

router = APIRouter(prefix="/presets", tags=["Presets"])

# {preset_id: {"engine": ScriptEngine|ScriptRunner, "thread": Thread, "execution_id": int}}
_running: dict[int, dict] = {}
# B9 修复: 线程安全锁保护 _running 并发读写
_running_lock = threading.Lock()


# B2 修复: flow_data 格式转换 — 旧版 steps → 新版 nodes 图
def _convert_steps_to_graph(steps: list) -> dict[str, dict]:
    """将旧版 steps 列表转为新版节点图"""
    nodes = {}
    for i, step in enumerate(steps):
        nid = step.get("id", f"step_{i}")
        action_type = step.get("action_type", step.get("condition_type", ""))
        config = {
            k: v for k, v in step.items()
            if k not in ("id", "action_type", "condition_type", "next", "enabled")
        }
        type_map = {
            "start": "start", "end": "end", "wait": "wait", "log": "log",
            "key": "key_press", "text": "text_output",
            "click_image": "mouse_click", "click_text": "mouse_click",
            "swipe": "mouse_drag", "screenshot": "screenshot",
        }
        node_type = type_map.get(action_type, "log")
        next_nodes = step.get("next", [])
        if not next_nodes and i + 1 < len(steps):
            next_nodes = [steps[i + 1].get("id", f"step_{i + 1}")]
        nodes[nid] = {"type": node_type, "config": config, "next": next_nodes}
    return nodes


def _build_runner_from_graph(graph: dict) -> "ScriptRunner":
    """从节点图构建 ScriptRunner 实例"""
    from engine.nodes import create_node as _create_node
    from engine.executor.runner import ScriptRunner

    node_instances = {}
    start_id = None

    for nid, ndef in graph.items():
        ntype = ndef.get("type", "log")
        config = ndef.get("config", {})
        node = _create_node(ntype, nid, config)
        node_instances[nid] = node
        if ntype == "start" and start_id is None:
            start_id = nid

    for nid, ndef in graph.items():
        node = node_instances.get(nid)
        if node:
            node.next_nodes = ndef.get("next", [])

    if start_id is None:
        start_id = next(iter(node_instances.keys()), "start")

    return ScriptRunner(node_instances, start_id)


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
    # B9: 加锁操作
    with _running_lock:
        state = _running.pop(preset_id, None)
    if state and state.get("engine"):
        state["engine"].stop()
    await db.delete(preset)
    await db.flush()
    return success({"deleted": True, "id": preset_id})


# ─── 执行控制 ───────────────────────────────────

@router.post("/{preset_id}/execute")
async def execute_preset(
    preset_id: int,
    engine_type: Optional[str] = Query(default=None,
                                       description="引擎类型: v1(旧) 或 v2(新)，默认自动检测"),
    db: AsyncSession = Depends(get_db),
):
    """执行预设 — 支持双引擎自动检测

    - 含 "nodes" 键 → 新引擎 ScriptRunner（async 图遍历）
    - 含 "steps" 键 → 旧引擎 ScriptEngine（同步线程）
    - 可通过 engine_type=v1 或 v2 强制指定
    """
    preset = await get_or_404(Preset, preset_id, db)

    # B9: 加锁检查
    with _running_lock:
        state = _running.get(preset_id)
    if state and state.get("thread") and state["thread"].is_alive():
        raise api_error("该预设正在执行中，请先停止", 409)

    # 解析 flow_data
    try:
        flow = json.loads(preset.flow_data) if isinstance(preset.flow_data, str) else preset.flow_data
    except (json.JSONDecodeError, TypeError):
        flow = {}

    # B2: 自动检测引擎类型
    use_v2 = engine_type == "v2" or (engine_type != "v1" and "nodes" in flow)
    steps = flow.get("steps", [])
    nodes_graph = flow.get("nodes", {})

    max_runs = flow.get("max_runs", 0)
    round_interval = flow.get("round_interval", 0)
    chain = flow.get("chain", True)

    # 创建执行记录
    now = datetime.now()
    execution = Execution(preset_id=preset_id, status="running", started_at=now)
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # 创建步骤记录
    if use_v2 and nodes_graph:
        for idx, (nid, ndef) in enumerate(nodes_graph.items()):
            db.add(ExecutionStep(
                execution_id=execution.id, step_order=idx + 1,
                node_id=nid, node_type=ndef.get("type", ""),
                status="pending",
                input_data=json.dumps(ndef, ensure_ascii=False),
            ))
    else:
        for idx, step in enumerate(steps):
            db.add(ExecutionStep(
                execution_id=execution.id, step_order=idx + 1,
                node_id=step.get("id", f"step_{idx}"),
                node_type=step.get("action_type", step.get("condition_type", "")),
                status="pending",
                input_data=json.dumps(step, ensure_ascii=False),
            ))
    await db.flush()

    eid = execution.id

    # B10 + R2 修复: _on_done 回调 — 通过 schedule_broadcast_status 线程安全广播
    def _on_done():
        try:
            conn = sqlite3.connect(DB_PATH)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with _running_lock:
                eng_state = _running.get(preset_id, {})
            eng = eng_state.get("engine")

            # 兼容新旧引擎的状态判断
            if eng:
                if hasattr(eng, "is_stopped") and eng.is_stopped():
                    status = "stopped"
                elif hasattr(eng, "monitor") and eng.monitor().get("error"):
                    status = "error"
                elif hasattr(eng, "state") and str(eng.state) == "error":
                    status = "error"
                elif hasattr(eng, "state") and str(eng.state) == "stopped":
                    status = "stopped"
                else:
                    status = "completed"
            else:
                status = "completed"
            duration = int((datetime.now() - execution.started_at).total_seconds() * 1000) \
                if execution.started_at else None
            error_msg = None
            if eng:
                if hasattr(eng, "monitor"):
                    error_msg = eng.monitor().get("error") or None
                elif hasattr(eng, "context") and eng.context:
                    error_logs = [l for l in eng.context.get_logs()
                                  if l.get("level") == "ERROR"]
                    error_msg = error_logs[-1]["message"] if error_logs else None
            conn.execute(
                "UPDATE executions SET status=?, finished_at=?, duration_ms=?, error_message=? WHERE id=?",
                (status, now_str, duration, error_msg, eid),
            )
            conn.commit()
            conn.close()

            # R2 修复: 使用 run_coroutine_threadsafe 从同步线程安全广播
            from app.api.websocket import schedule_broadcast_status
            schedule_broadcast_status(eid, {
                "execution_id": eid, "preset_id": preset_id,
                "status": status, "finished_at": now_str,
                "duration_ms": duration, "error_message": error_msg,
                "timestamp": now_str,
            })
        except Exception:
            pass

    if use_v2 and nodes_graph:
        # B2: 新引擎 ScriptRunner
        runner = _build_runner_from_graph(nodes_graph)

        def _bg_run_v2():
            import asyncio as _asyncio
            # B8: 注册 engine 到共享状态
            with _running_lock:
                if preset_id in _running:
                    _running[preset_id]["engine"] = runner
            try:
                _asyncio.run(runner.run())
            except Exception as e:
                pass
            finally:
                _on_done()
                with _running_lock:
                    _running.pop(preset_id, None)

        t = threading.Thread(target=_bg_run_v2, daemon=True)
        with _running_lock:
            _running[preset_id] = {"engine": runner, "thread": t, "execution_id": eid}
        t.start()
    else:
        # 旧引擎 ScriptEngine
        def _bg_run():
            from engine.engine import ScriptEngine
            eng = ScriptEngine()
            eng.running = True
            eng._stop_ev.clear()
            # B8 修复: 写回 engine 引用到共享状态
            with _running_lock:
                if preset_id in _running:
                    _running[preset_id]["engine"] = eng
            try:
                eng.run(
                    {"name": preset.name, "steps": steps,
                     "max_runs": max_runs, "round_interval": round_interval, "chain": chain},
                    chain=chain, on_done=_on_done,
                )
            except Exception:
                pass
            finally:
                with _running_lock:
                    _running.pop(preset_id, None)

        t = threading.Thread(target=_bg_run, daemon=True)
        with _running_lock:
            _running[preset_id] = {"engine": None, "thread": t, "execution_id": eid}
        t.start()

    engine_label = "v2 (ScriptRunner)" if (use_v2 and nodes_graph) else "v1 (ScriptEngine)"
    return success({"execution_id": eid, "status": "running",
                     "engine": engine_label,
                     "message": f"预设 «{preset.name}» 已启动"})


@router.post("/{preset_id}/stop")
async def stop_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """停止执行"""
    # B9: 加锁读取
    with _running_lock:
        state = _running.get(preset_id)
        if not state or not state.get("thread") or not state["thread"].is_alive():
            raise api_error("该预设未在运行", 409)

        eng = state.get("engine")
        if eng:
            eng.stop()

        eid = state.get("execution_id")

    # 更新执行记录状态
    if eid:
        result = await db.execute(select(Execution).where(Execution.id == eid))
        ex = result.scalar_one_or_none()
        if ex and ex.status == "running":
            ex.status = "stopped"
            ex.finished_at = datetime.now()
            if ex.started_at:
                ex.duration_ms = int((datetime.now() - ex.started_at).total_seconds() * 1000)
            await db.flush()
        # B10/R2: 线程安全广播停止状态
        from app.api.websocket import schedule_broadcast_status
        schedule_broadcast_status(eid, {
            "execution_id": eid, "preset_id": preset_id,
            "status": "stopped", "finished_at": datetime.now().isoformat(),
        })

    return success({"stopped": True, "preset_id": preset_id})


@router.post("/{preset_id}/pause")
async def pause_preset(preset_id: int):
    """暂停 — 当前轮完成后自动停止"""
    with _running_lock:
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
    with _running_lock:
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
    with _running_lock:
        state = _running.get(preset_id)
        if not state or not state.get("thread") or not state["thread"].is_alive():
            raise api_error("该预设未在运行", 409)

        eng = state.get("engine")
        if eng:
            current = eng.monitor().get("step", 0)
            eng.stop_after = current + 1 if current > 0 else 1
    return success({"step": True, "preset_id": preset_id})
