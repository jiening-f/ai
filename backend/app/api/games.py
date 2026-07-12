"""
游戏管理 API 路由

- GET /api/games — 列表
- POST /api/games — 创建
- GET /api/games/{id} — 详情
- PUT /api/games/{id} — 更新
- DELETE /api/games/{id} — 删除
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.game import Game
from app.schemas.game import GameCreate, GameUpdate, GameOut, ApiResponse

router = APIRouter(tags=["游戏管理"])


@router.get("/games", response_model=ApiResponse)
async def list_games(
    name: str = Query(default=None, description="按名称搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取游戏列表，支持按名称搜索"""
    stmt = select(Game)
    if name:
        stmt = stmt.where(Game.name.contains(name))
    stmt = stmt.order_by(Game.created_at.desc())

    result = await db.execute(stmt)
    games = result.scalars().all()

    return ApiResponse(
        success=True,
        data=[
            {
                "id": g.id, "name": g.name,
                "window_title": g.window_title, "window_class": g.window_class,
                "created_at": str(g.created_at), "updated_at": str(g.updated_at),
            }
            for g in games
        ],
    )


@router.post("/games", response_model=ApiResponse, status_code=201)
async def create_game(body: GameCreate, db: AsyncSession = Depends(get_db)):
    """创建游戏"""
    game = Game(
        name=body.name,
        window_title=body.window_title,
        window_class=body.window_class,
    )
    db.add(game)
    await db.flush()
    await db.refresh(game)

    return ApiResponse(
        success=True,
        data={
            "id": game.id, "name": game.name,
            "window_title": game.window_title, "window_class": game.window_class,
            "created_at": str(game.created_at), "updated_at": str(game.updated_at),
        },
    )


@router.get("/games/{game_id}", response_model=ApiResponse)
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """获取游戏详情"""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    return ApiResponse(
        success=True,
        data={
            "id": game.id, "name": game.name,
            "window_title": game.window_title, "window_class": game.window_class,
            "created_at": str(game.created_at), "updated_at": str(game.updated_at),
        },
    )


@router.put("/games/{game_id}", response_model=ApiResponse)
async def update_game(game_id: int, body: GameUpdate, db: AsyncSession = Depends(get_db)):
    """更新游戏"""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    if body.name is not None:
        game.name = body.name
    if body.window_title is not None:
        game.window_title = body.window_title
    if body.window_class is not None:
        game.window_class = body.window_class

    await db.flush()
    await db.refresh(game)

    return ApiResponse(
        success=True,
        data={
            "id": game.id, "name": game.name,
            "window_title": game.window_title, "window_class": game.window_class,
            "created_at": str(game.created_at), "updated_at": str(game.updated_at),
        },
    )


@router.delete("/games/{game_id}", response_model=ApiResponse)
async def delete_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """删除游戏"""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    await db.delete(game)
    await db.flush()
    return ApiResponse(success=True, data={"deleted_id": game_id})
