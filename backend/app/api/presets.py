"""预设管理 API 路由 + 执行控制"""

import asyncio
import json
import datetime
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.preset import Preset
from app.models.execution import Execution
from app.schemas.preset import PresetCreate, PresetUpdate, PresetOut
from app.schemas.game import ApiResponse

# ScriptEngine 从项目根目录的 engine/ 包导入
from engine.engine import ScriptEngine

router = APIRouter(tags=["预设管理"])

# ── 存储运行中的 ScriptEngine 实例 ──
_execution_lock = asyncio.Lock()
_running_executions: dict[int, ScriptEngine] = {}  # execution_id → engine


# ── CRUD ───────────────────────────

@router.get("/presets", response_model=ApiResponse)
async def list_presets(
    game_id: int = Query(default=None, description="按游戏 ID 筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取预设列表，可选按游戏筛选"""
    stmt = select(Preset)
    if game_id:
        stmt = stmt.where(Preset.game_id == game_id)
    stmt = stmt.order_by(Preset.created_at.desc())

    result = await db.execute(stmt)
    presets = result.scalars().all()

    return ApiResponse(success=True, data=[
        {
            "id": p.id, "game_id": p.game_id, "name": p.name,
            "description": p.description, "is_active": p.is_active,
            "created_at": str(p.created_at),
        }
        for p in presets
    ])


@router.post("/presets", response_model=ApiResponse, status_code=201)
async def create_preset(body: PresetCreate, db: AsyncSession = Depends(get_db)):
    """创建预设"""
    preset = Preset(
        game_id=body.game_id, name=body.name,
        description=body.description, flow_data=body.flow_data,
        is_active=body.is_active,
    )
    db.add(preset)
    await db.flush()
    await db.refresh(preset)

    return ApiResponse(success=True, data=_preset_to_dict(preset))


@router.get("/presets/{preset_id}", response_model=ApiResponse)
async def get_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """获取预设详情（含 flow_data）"""
    result = await db.execute(select(Preset).where(Preset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")
    return ApiResponse(success=True, data=_preset_to_dict(preset))


@router.put("/presets/{preset_id}", response_model=ApiResponse)
async def update_preset(preset_id: int, body: PresetUpdate, db: AsyncSession = Depends(get_db)):
    """更新预设"""
    result = await db.execute(select(Preset).where(Preset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    if body.name is not None:
        preset.name = body.name
    if body.description is not None:
        preset.description = body.description
    if body.flow_data is not None:
        preset.flow_data = body.flow_data
    if body.is_active is not None:
        preset.is_active = body.is_active

    await db.flush()
    await db.refresh(preset)
    return ApiResponse(success=True, data=_preset_to_dict(preset))


@router.delete("/presets/{preset_id}", response_model=ApiResponse)
async def delete_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """删除预设"""
    result = await db.execute(select(Preset).where(Preset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    await db.delete(preset)
    await db.flush()
    return ApiResponse(success=True, data={"deleted_id": preset_id})


# ── 执行控制 ────────────────────────

@router.post("/presets/{preset_id}/execute", response_model=ApiResponse)
async def execute_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """执行预设（启动引擎）"""
    result = await db.execute(select(Preset).where(Preset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 解析 flow_data
    try:
        flow_data = json.loads(preset.flow_data) if isinstance(preset.flow_data, str) else preset.flow_data
    except json.JSONDecodeError:
        return ApiResponse(success=False, error="flow_data 格式错误，无法解析为 JSON")

    if not flow_data:
        return ApiResponse(success=False, error="预设没有流程数据")

    # 转换为 ScriptEngine 能用的 preset 格式
    preset_dict = _flow_to_preset(flow_data, preset.name)

    # 创建执行记录
    execution = Execution(
        preset_id=preset_id,
        status="running",
        started_at=datetime.datetime.utcnow(),
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # 启动引擎（后台线程）
    engine = ScriptEngine()
    engine.background_mode = False

    async with _execution_lock:
        _running_executions[execution.id] = engine

    t = threading.Thread(
        target=_bg_run,
        args=(engine, preset_dict, execution.id, preset_id, preset.name),
        daemon=True,
    )
    t.start()

    return ApiResponse(success=True, data={
        "execution_id": execution.id,
        "message": "脚本已启动",
    })


@router.post("/presets/{preset_id}/stop", response_model=ApiResponse)
async def stop_execution(preset_id: int, db: AsyncSession = Depends(get_db)):
    """停止执行"""
    # 查找最近的 running/paused 状态的执行
    stmt = select(Execution).where(
        Execution.preset_id == preset_id,
        Execution.status.in_(["running", "paused"]),
    ).order_by(Execution.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution and execution.id in _running_executions:
        _running_executions[execution.id].stop()
        return ApiResponse(success=True, data={"message": "停止指令已发送"})
    return ApiResponse(success=False, error="没有正在运行的执行")


@router.post("/presets/{preset_id}/pause", response_model=ApiResponse)
async def pause_execution(preset_id: int, db: AsyncSession = Depends(get_db)):
    """暂停执行"""
    stmt = select(Execution).where(
        Execution.preset_id == preset_id,
        Execution.status == "running",
    ).order_by(Execution.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution and execution.id in _running_executions:
        _running_executions[execution.id].pause()
        return ApiResponse(success=True, data={"message": "暂停指令已发送"})
    return ApiResponse(success=False, error="没有正在运行的执行")


@router.post("/presets/{preset_id}/resume", response_model=ApiResponse)
async def resume_execution(preset_id: int, db: AsyncSession = Depends(get_db)):
    """恢复执行"""
    stmt = select(Execution).where(
        Execution.preset_id == preset_id,
        Execution.status == "paused",
    ).order_by(Execution.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution and execution.id in _running_executions:
        _running_executions[execution.id].resume()
        return ApiResponse(success=True, data={"message": "恢复指令已发送"})
    return ApiResponse(success=False, error="没有处于暂停状态的执行")


@router.post("/presets/{preset_id}/step", response_model=ApiResponse)
async def step_execution(preset_id: int, db: AsyncSession = Depends(get_db)):
    """单步执行：暂停状态下恢复执行一步"""
    stmt = select(Execution).where(
        Execution.preset_id == preset_id,
        Execution.status.in_(["running", "paused"]),
    ).order_by(Execution.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution and execution.id in _running_executions:
        engine = _running_executions[execution.id]
        engine.resume()  # 恢复执行
        return ApiResponse(success=True, data={"message": "已恢复执行"})
    return ApiResponse(success=False, error="没有正在运行的执行")


# ── 辅助函数 ────────────────────────

def _preset_to_dict(p: Preset) -> dict:
    return {
        "id": p.id, "game_id": p.game_id, "name": p.name,
        "description": p.description, "flow_data": p.flow_data,
        "is_active": p.is_active,
        "created_at": str(p.created_at), "updated_at": str(p.updated_at),
    }


def _bg_run(engine, preset_dict: dict, execution_id: int,
             preset_id: int, preset_name: str):
    """后台线程：执行 ScriptEngine 并更新数据库

    此函数在单独线程中同步运行，通过 engine 的启停机制控制。
    """
    error_msg = [None]  # 用列表在线程间共享
    status = ["stopped"]  # 默认 stopped

    def on_log(msg: str):
        """执行日志回调 — 可用于后续写入 ExecutionStep"""
        pass

    def on_done():
        """执行完成回调"""
        nonlocal status
        status[0] = "completed"

    started = datetime.datetime.utcnow()
    try:
        engine.run(preset_dict, chain=True, on_log=on_log, on_done=on_done)
    except Exception as e:
        error_msg[0] = str(e)
        status[0] = "error"

    # 检查是否被主动停止
    if engine.is_stopped() and status[0] != "error":
        status[0] = "stopped"

    finished = datetime.datetime.utcnow()
    duration_ms = int((finished - started).total_seconds() * 1000)

    # 异步更新数据库
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _update_db():
        from app.database import async_session_factory
        async with async_session_factory() as db:
            result = await db.execute(select(Execution).where(Execution.id == execution_id))
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = status[0]
                execution.finished_at = finished
                execution.duration_ms = duration_ms
                if error_msg[0]:
                    execution.error_message = error_msg[0]
                await db.commit()

    loop.run_until_complete(_update_db())

    # 从运行字典中移除
    asyncio.run_coroutine_threadsafe(
        _cleanup_execution(execution_id),
        loop,
    )


async def _cleanup_execution(execution_id: int):
    """从 _running_executions 中移除已完成的执行"""
    async with _execution_lock:
        _running_executions.pop(execution_id, None)


def _flow_to_preset(flow_data: dict, name: str = "") -> dict:
    """将 flow_data（节点流程 JSON）转换为 ScriptEngine 兼容的 preset dict

    支持两种格式：
    1. 旧预设格式：{"steps": [...], "max_runs": N, "round_interval": N, "chain": bool}
    2. 新节点格式：{"maps": [...], "loop_enabled": bool, "max_loops": N}
    """
    # 如果已经是旧格式，直接使用
    if "steps" in flow_data:
        return {
            "name": name,
            "game": flow_data.get("game", "未分类"),
            "steps": flow_data.get("steps", []),
            "max_runs": flow_data.get("max_runs", 0),
            "round_interval": flow_data.get("round_interval", 0),
            "chain": flow_data.get("chain", True),
        }

    # 新节点格式 → 旧预设格式的适配转换
    steps = []
    for map_cfg in flow_data.get("maps", []):
        if not map_cfg.get("enabled", True):
            continue
        for feature in map_cfg.get("features", []):
            if not feature.get("enabled", True):
                continue
            # 将特征节点转为步骤
            detect_type = feature.get("detect_type", "text")
            detect_value = feature.get("detect_value", "")

            step = {
                "condition_type": "none",
                "condition_value": "",
                "action_type": "press_key",
                "action_value": "space",
                "duration": 0.2,
                "delay": 0,
                "count": 0,
                "enabled": True,
                "verify_text": "",
            }

            if detect_type == "text":
                step["condition_type"] = "text"
                step["condition_value"] = detect_value
            elif detect_type == "image":
                step["condition_type"] = "image"
                step["condition_value"] = detect_value
                step["action_type"] = "click_image"
                step["action_value"] = detect_value

            # on_match 和 on_mismatch 在 NodeEngine 中处理，
            # ScriptEngine 通过 chain 参数控制是否中断
            steps.append(step)

    return {
        "name": name,
        "game": "未分类",
        "steps": steps if steps else [],
        "max_runs": flow_data.get("max_loops", 0),
        "round_interval": 0,
        "chain": False,  # 节点模式不链式中断
    }
