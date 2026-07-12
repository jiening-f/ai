"""
预设管理 API 路由 + 执行控制

- GET /api/presets?game_id={id} — 列表
- POST /api/presets — 创建
- GET /api/presets/{id} — 详情（含 flow_data）
- PUT /api/presets/{id} — 更新
- DELETE /api/presets/{id} — 删除
- POST /api/presets/{id}/execute — 执行
- POST /api/presets/{id}/stop — 停止
- POST /api/presets/{id}/pause — 暂停
- POST /api/presets/{id}/resume — 恢复
- POST /api/presets/{id}/step — 单步
"""

import asyncio
import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.preset import Preset
from app.models.execution import Execution
from app.schemas.preset import PresetCreate, PresetUpdate, PresetOut
from app.schemas.game import ApiResponse

router = APIRouter(tags=["预设管理"])

# ── 存储运行中的 ScriptRunner 实例 ──
_running_executions: dict[int, "ScriptRunner"] = {}  # execution_id → runner
_execution_lock = asyncio.Lock()


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

    # 创建执行记录
    execution = Execution(preset_id=preset_id, status="running")
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # 创建 runner 并立即注册（消除 create_task 前的窗口期）
    from engine.executor.context import ExecutionContext
    from engine.executor.runner import ScriptRunner
    from engine.executor.hooks import HookManager

    ctx = ExecutionContext(str(execution.id))
    hooks = HookManager()
    runner = ScriptRunner(ctx, flow_data, hooks)

    async with _execution_lock:
        _running_executions[execution.id] = runner

    # 启动引擎（后台任务）
    asyncio.create_task(_run_flow(runner))

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
    """单步执行"""
    stmt = select(Execution).where(
        Execution.preset_id == preset_id,
        Execution.status.in_(["running", "paused"]),
    ).order_by(Execution.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution and execution.id in _running_executions:
        await _running_executions[execution.id].step()
        return ApiResponse(success=True, data={"message": "已执行单步"})
    return ApiResponse(success=False, error="没有正在运行的执行")


# ── 辅助函数 ────────────────────────

def _preset_to_dict(p: Preset) -> dict:
    return {
        "id": p.id, "game_id": p.game_id, "name": p.name,
        "description": p.description, "flow_data": p.flow_data,
        "is_active": p.is_active,
        "created_at": str(p.created_at), "updated_at": str(p.updated_at),
    }


async def _run_flow(runner: "ScriptRunner"):
    """后台执行脚本流程（runner 已在调用方注册到 _running_executions）"""
    import datetime
    from engine.executor.context import ExecutionContext
    from engine.executor.runner import ScriptRunner
    from app.models.execution import Execution
    from app.database import async_session_factory

    ctx = runner.ctx
    execution_id = int(ctx.execution_id)
    success = False
    try:
        success = await runner.run()
    finally:
        # 更新执行记录
        async with async_session_factory() as db:
            result = await db.execute(select(Execution).where(Execution.id == execution_id))
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = (
                    "completed" if success
                    else "error" if ctx.status.value == "error"
                    else "stopped"
                )
                execution.finished_at = datetime.datetime.utcnow()
                execution.duration_ms = int(ctx.elapsed_ms)
                await db.commit()

        async with _execution_lock:
            _running_executions.pop(execution_id, None)
