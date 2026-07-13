import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { executionsApi, Execution } from '../api/executions'
import { useToast } from '../components/ui/Toast'
import { useSSE } from '../hooks/useSSE'

const statusBadge: Record<string, string> = {
  running: 'badge-running',
  paused: 'badge-paused',
  completed: 'badge-completed',
  error: 'badge-error',
  stopped: 'badge-stopped',
}

function Dashboard() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 实时日志流
  const [logLines, setLogLines] = useState<string[]>([])
  const [logConnected, setLogConnected] = useState(false)
  const [logPaused, setLogPaused] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)
  const { connected: sseConnected, on } = useSSE('/api/logs/stream')

  useEffect(() => {
    setLogConnected(sseConnected)
  }, [sseConnected])

  useEffect(() => {
    // 监听初始日志数据
    const unsubInit = on('init', (data: unknown) => {
      const d = data as { lines?: string[] }
      if (d.lines) {
        setLogLines(d.lines)
      }
    })
    // 监听实时日志行
    const unsubMsg = on('message', (data: unknown) => {
      if (!logPaused) {
        const d = data as { line?: string }
        if (d.line) {
          setLogLines((prev) => [...prev.slice(-200), d.line!])
        }
      }
    })
    return () => {
      unsubInit()
      unsubMsg()
    }
  }, [on, logPaused])

  // 自动滚动到底部
  useEffect(() => {
    if (!logPaused) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logLines, logPaused])

  const statsCards = [
    { title: '预设总数', value: '0', desc: '所有游戏' },
    { title: '今日执行', value: '0', desc: '24 小时内' },
    { title: '执行成功率', value: '-', desc: '最近 50 次' },
    { title: '活跃插件', value: '0', desc: '已启用' },
  ]

  useEffect(() => {
    executionsApi
      .list({ page_size: 10 })
      .then((res) => setRecentExecutions(res.items))
      .catch((err) => {
        setError(err.message)
        // 后端不可用时用空数据
        setRecentExecutions([])
      })
      .finally(() => setLoading(false))
  }, [])

  const handleExecute = () => {
    toast({ type: 'info', title: '请先选择一个预设', description: '前往预设编辑页面创建预设' })
    navigate('/presets/0')
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatTime = (t: string | null) => {
    if (!t) return '-'
    const d = new Date(t)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="page">
      <h1>仪表盘</h1>

      {/* 状态卡片 */}
      <div className="card-grid">
        {statsCards.map((card) => (
          <div className="card" key={card.title}>
            <div className="card-title">{card.title}</div>
            <div className="card-value">{card.value}</div>
            <div className="text-secondary mt-sm text-small">{card.desc}</div>
          </div>
        ))}
      </div>

      {/* 快捷操作 */}
      <div className="section">
        <h2>快捷操作</h2>
        <div className="quick-actions">
          <button className="btn btn-primary" onClick={handleExecute}>
            ▶ 新建预设
          </button>
          <button className="btn" onClick={() => navigate('/games')}>
            🎮 管理游戏
          </button>
          <button className="btn" onClick={() => navigate('/history')}>
            📋 查看历史
          </button>
        </div>
      </div>

      {/* 最近执行 */}
      <div className="section">
        <div className="section-header">
          <h2>最近执行</h2>
          <button className="btn btn-sm" onClick={() => navigate('/history')}>
            查看全部 →
          </button>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /> 加载中...</div>
        ) : error && recentExecutions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <div className="empty-state-text">暂无执行记录</div>
            <button className="btn btn-sm" onClick={() => window.location.reload()}>
              刷新
            </button>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>预设</th>
                  <th>状态</th>
                  <th>耗时</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {recentExecutions.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-tertiary)' }}>
                      暂无执行记录
                    </td>
                  </tr>
                ) : (
                  recentExecutions.map((exec) => (
                    <tr key={exec.id}>
                      <td>{exec.preset_name || `预设 #${exec.preset_id}`}</td>
                      <td><span className={`badge ${statusBadge[exec.status] || 'badge-neutral'}`}>{exec.status}</span></td>
                      <td>{formatDuration(exec.duration_ms)}</td>
                      <td className="text-tertiary text-small">{formatTime(exec.started_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 实时日志流 */}
      <div className="section">
        <div className="section-header">
          <h2>实时日志</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span className={`badge ${logConnected ? 'badge-completed' : 'badge-error'}`}>
              {logConnected ? '已连接' : '未连接'}
            </span>
            <button
              className="btn btn-sm"
              onClick={() => setLogPaused(!logPaused)}
            >
              {logPaused ? '▶ 继续' : '⏸ 暂停'}
            </button>
            <button
              className="btn btn-sm"
              onClick={() => setLogLines([])}
            >
              🗑 清空
            </button>
          </div>
        </div>
        <div
          style={{
            background: '#0a0a1a',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-md)',
            maxHeight: 300,
            overflowY: 'auto',
            fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", monospace',
            fontSize: 12,
            lineHeight: 1.6,
            color: '#a5b4fc',
          }}
        >
          {logLines.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 'var(--space-lg)' }}>
              {logConnected ? '等待日志...' : '正在连接日志服务...'}
            </div>
          ) : (
            logLines.map((line, i) => (
              <div key={i} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {line}
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard
