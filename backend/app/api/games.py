"""Games 游戏管理 API — CRUD"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from database.models import Game
from app.schemas.game import GameCreate, GameUpdate, GameResponse
from app.api import success, get_or_404

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("")
async def list_games(
    name: str = Query(default=None, description="按名称模糊搜索"),
    db: AsyncSession = Depends(get_db),
):
    """游戏列表，支持 name 搜索"""
    stmt = select(Game).order_by(Game.updated_at.desc())
    if name:
        stmt = stmt.where(Game.name.contains(name))
    result = await db.execute(stmt)
    games = result.scalars().all()
    return success([GameResponse.model_validate(g).model_dump(mode="json") for g in games])


@router.post("", status_code=201)
async def create_game(body: GameCreate, db: AsyncSession = Depends(get_db)):
    """创建游戏"""
    game = Game(name=body.name, window_title=body.window_title, window_class=body.window_class)
    db.add(game)
    await db.flush()
    await db.refresh(game)
    return success(GameResponse.model_validate(game).model_dump(mode="json"))


@router.get("/{game_id}")
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """游戏详情"""
    game = await get_or_404(Game, game_id, db)
    return success(GameResponse.model_validate(game).model_dump(mode="json"))


@router.put("/{game_id}")
async def update_game(game_id: int, body: GameUpdate, db: AsyncSession = Depends(get_db)):
    """更新游戏"""
    game = await get_or_404(Game, game_id, db)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(game, k, v)
    game.updated_at = datetime.now()
    await db.flush()
    await db.refresh(game)
    return success(GameResponse.model_validate(game).model_dump(mode="json"))


@router.delete("/{game_id}")
async def delete_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """删除游戏（级联删除预设+执行记录+步骤日志）"""
    game = await get_or_404(Game, game_id, db)
    await db.delete(game)
    await db.flush()
    return success({"deleted": True, "id": game_id})
