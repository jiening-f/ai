"""SSE 日志流端点 — 实时日志推送"""
import asyncio
import os
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from core.constants import LOG_FILE

router = APIRouter(tags=["Logs"])


@router.get("/logs")
async def get_logs(
    lines: int = Query(default=100, ge=1, le=1000, description="返回最近 N 行日志"),
):
    """获取最近的日志行"""
    if not os.path.exists(LOG_FILE):
        return {"success": True, "data": {"lines": [], "total": 0}, "error": None}

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "success": True,
            "data": {
                "lines": [ln.rstrip("\n") for ln in recent],
                "total": len(all_lines),
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


@router.get("/logs/stream")
async def stream_logs(request: Request):
    """SSE 日志流 — 实时推送新日志行"""

    async def event_generator():
        # 记录当前文件大小，后续只推送新增内容
        last_pos = 0
        if os.path.exists(LOG_FILE):
            last_pos = os.path.getsize(LOG_FILE)

        # 首先发送最近 20 行作为初始数据
        initial_lines = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                initial_lines = [ln.rstrip("\n") for ln in all_lines[-20:]] if len(all_lines) > 20 else [ln.rstrip("\n") for ln in all_lines]
            except Exception:
                pass

        yield f"event: init\ndata: {__import__('json').dumps({'lines': initial_lines})}\n\n"

        # 持续监控文件新增内容
        while True:
            if await request.is_disconnected():
                break

            try:
                if os.path.exists(LOG_FILE):
                    current_size = os.path.getsize(LOG_FILE)
                    if current_size > last_pos:
                        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_pos)
                            new_content = f.read()
                        last_pos = current_size
                        for line in new_content.splitlines():
                            line = line.strip()
                            if line:
                                yield f"data: {__import__('json').dumps({'line': line})}\n\n"
                    elif current_size < last_pos:
                        # 文件被截断了，从头开始
                        last_pos = 0
            except Exception:
                pass

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
