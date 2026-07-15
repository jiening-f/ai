import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { executionsApi, Execution } from '../api/executions'

const statusBadge: Record<string, string> = {
  running: 'badge-running',
  paused: 'badge-paused',
  completed: 'badge-completed',
  error: 'badge-error',
  stopped: 'badge-stopped',
}

const statusLabel: Record<string, string> = {
  running: '运行中',
  paused: '已暂停',
  completed: '已完成',
  error: '出错',
  stopped: '已停止',
}

function Dashboard() {
  const navigate = useNavigate()
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 统计指标
  const stats = [
    { label: '已添加游戏', value: '5', icon: '🎮', color: 'purple' },
    { label: '预设总数', value: '12', icon: '📋', color: 'blue' },
    { label: '今日运行', value: '3', icon: '▶', color: 'green' },
    { label: '活跃插件', value: '7', icon: '🧩', color: 'orange' },
  ]

  useEffect(() => {
    executionsApi
      .list({ limit: 10 })
      .then(setRecentExecutions)
      .catch((err) => {
        setError(err.message)
        setRecentExecutions([])
      })
      .finally(() => setLoading(false))
  }, [])

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
      {/* 统计卡片 */}
      <div className="stat-card-grid">
        {stats.map((stat) => (
          <div className="stat-card" key={stat.label}>
            <div className={`stat-card-icon ${stat.color}`}>{stat.icon}</div>
            <div className="stat-card-body">
              <div className="stat-card-label">{stat.label}</div>
              <div className="stat-card-value">{stat.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 快捷操作 */}
      <div className="section">
        <h2>快捷操作</h2>
        <div className="quick-actions">
          <button className="btn btn-primary" onClick={() => navigate('/presets/0')}>
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
                      <td>
                        <span className={`badge ${statusBadge[exec.status] || 'badge-neutral'}`}>
                          {statusLabel[exec.status] || exec.status}
                        </span>
                      </td>
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
    </div>
  )
}

export default Dashboard
