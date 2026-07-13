import { useEffect, useRef, useCallback, useState } from 'react'

type MessageHandler = (data: unknown) => void

/** 安全解析 JSON，失败时返回原始文本 */
function tryParse(data: string): unknown {
  try {
    return JSON.parse(data)
  } catch {
    return data
  }
}

/**
 * SSE (Server-Sent Events) Hook
 * 用于连接到后端的实时日志流端点，支持自动重连
 */
export function useSSE(url: string) {
  const sourceRef = useRef<EventSource | null>(null)
  const handlersRef = useRef<Map<string, MessageHandler[]>>(new Map())
  const [connected, setConnected] = useState(false)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    // 关闭之前的连接
    if (sourceRef.current) {
      sourceRef.current.close()
    }

    const es = new EventSource(url)
    sourceRef.current = es

    es.onopen = () => setConnected(true)

    es.onerror = () => {
      setConnected(false)
      es.close()
      // 3 秒后重连
      reconnectTimerRef.current = setTimeout(connect, 3000)
    }

    // 通用 message 事件
    es.onmessage = (event: MessageEvent) => {
      const data = tryParse(event.data)
      const handlers = handlersRef.current.get('message') || []
      handlers.forEach((fn) => fn(data))
    }

    // 具名事件监听
    const eventTypes = ['init', 'log', 'status', 'error']
    eventTypes.forEach((type) => {
      es.addEventListener(type, (event: Event) => {
        const me = event as MessageEvent
        const data = tryParse(me.data)
        const handlers = handlersRef.current.get(type) || []
        handlers.forEach((fn) => fn(data))
      })
    })
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimerRef.current)
      sourceRef.current?.close()
    }
  }, [connect])

  const on = useCallback((type: string, handler: MessageHandler) => {
    const handlers = handlersRef.current.get(type) || []
    handlers.push(handler)
    handlersRef.current.set(type, handlers)
    return () => {
      const h = handlersRef.current.get(type) || []
      handlersRef.current.set(
        type,
        h.filter((fn) => fn !== handler),
      )
    }
  }, [])

  const close = useCallback(() => {
    clearTimeout(reconnectTimerRef.current)
    sourceRef.current?.close()
    setConnected(false)
  }, [])

  return { connected, on, close }
}
