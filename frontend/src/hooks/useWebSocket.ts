import { useEffect, useRef, useCallback, useState } from 'react'

type MessageHandler = (data: unknown) => void

interface UseWebSocketOptions {
  /** 是否启用连接，false 时不建立 WebSocket */
  enabled?: boolean
}

export function useWebSocket(path: string, options: UseWebSocketOptions = {}) {
  const { enabled = true } = options
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, MessageHandler[]>>(new Map())
  const [connected, setConnected] = useState(false)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = '127.0.0.1:8765'
    const url = `${protocol}//${host}${path}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      wsRef.current = null
      reconnectTimerRef.current = setTimeout(connect, 3000)
    }
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const type = msg.type || 'message'
        const handlers = handlersRef.current.get(type) || []
        handlers.forEach((fn) => fn(msg))
      } catch {
        // ignore parse errors
      }
    }
  }, [path])

  useEffect(() => {
    if (!enabled) {
      setConnected(false)
      // 关闭已有连接
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
      wsRef.current = null
      return
    }
    connect()
    return () => {
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect, enabled])

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

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, on, send }
}
