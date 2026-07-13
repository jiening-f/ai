"""事件桥 — 线程安全的事件广播，连接同步引擎线程和异步 WebSocket/SSE"""
import asyncio
import threading
from typing import Optional


class EventBridge:
    """线程安全事件桥

    同步引擎线程通过 push() 推送事件，
    异步 WebSocket/SSE 端点通过 subscribe() 获取 asyncio.Queue 接收事件。
    """

    def __init__(self):
        self._queues: dict[int, list[asyncio.Queue]] = {}
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """设置事件循环引用（在第一个异步端点连接时调用）"""
        self._loop = loop

    def subscribe(self, execution_id: int) -> asyncio.Queue:
        """订阅某个执行的事件流，返回 asyncio.Queue"""
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        with self._lock:
            if execution_id not in self._queues:
                self._queues[execution_id] = []
            self._queues[execution_id].append(q)
        return q

    def unsubscribe(self, execution_id: int, queue: asyncio.Queue):
        """取消订阅"""
        with self._lock:
            queues = self._queues.get(execution_id, [])
            if queue in queues:
                queues.remove(queue)
            if not queues:
                self._queues.pop(execution_id, None)

    def push(self, execution_id: int, event: dict):
        """从任意线程推送事件到所有订阅者"""
        with self._lock:
            queues = list(self._queues.get(execution_id, []))
        loop = self._loop
        if loop and loop.is_running():
            for q in queues:
                try:
                    loop.call_soon_threadsafe(q.put_nowait, event)
                except asyncio.QueueFull:
                    pass  # 队列满时丢弃旧事件


# 全局单例
event_bridge = EventBridge()
