"""SSE 日志流端点 — 实时日志推送"""
import asyncio
import json
import os
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from core.constants import LOG_FILE

router = APIRouter(tags=["Logs"])

# 估算每行字节数，用于 seek 定位
_EST_LINE_BYTES = 200


def _read_tail_lines(filepath: str, count: int) -> list[str]:
    """只读文件末尾 count 行，不加载整个文件到内存"""
    if not os.path.exists(filepath):
        return []
    try:
        fsize = os.path.getsize(filepath)
        if fsize == 0:
            return []
        # 预估需要读取的字节数
        estimate = min(fsize, count * _EST_LINE_BYTES)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(max(0, fsize - estimate))
            buf = f.read()
        lines = buf.splitlines()
        # 如果 seek 到了一行的中间，丢弃第一条不完整的行
        # 若读取的起始位置不是文件开头，第一行可能不完整
        if estimate < fsize and lines:
            lines = lines[1:]
        return [ln.rstrip("\n") for ln in lines[-count:]] if len(lines) > count else [ln.rstrip("\n") for ln in lines]
    except Exception:
        return []


def _count_lines(filepath: str) -> int:
    """高效文件行数统计"""
    if not os.path.exists(filepath):
        return 0
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                count += 1
    except Exception:
        pass
    return count


@router.get("/logs")
async def get_logs(
    lines: int = Query(default=100, ge=1, le=1000, description="返回最近 N 行日志"),
):
    """获取最近的日志行"""
    if not os.path.exists(LOG_FILE):
        return {"success": True, "data": {"lines": [], "total": 0}, "error": None}

    try:
        recent = _read_tail_lines(LOG_FILE, lines)
        total = _count_lines(LOG_FILE)
        return {
            "success": True,
            "data": {"lines": recent, "total": total},
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
        initial_lines = _read_tail_lines(LOG_FILE, 20)

        yield f"event: init\ndata: {json.dumps({'lines': initial_lines})}\n\n"

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
                                yield f"data: {json.dumps({'line': line})}\n\n"
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
