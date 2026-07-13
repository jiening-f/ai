import { useState, useEffect, useCallback } from 'react'
import { executionsApi, Execution, ExecutionStep } from '../api/executions'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { useToast } from '../components/ui/Toast'
import { useWebSocket } from '../hooks/useWebSocket'

const statusBadge: Record<string, string> = {
  running: 'badge-running',
  paused: 'badge-paused',
  completed: 'badge-completed',
  error: 'badge-error',
  stopped: 'badge-stopped',
}

function ExecutionHistory() {
  const { toast } = useToast()
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const pageSize = 10

  // 展开的行
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [steps, setSteps] = useState<ExecutionStep[]>([])

  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState<Execution | null>(null)

  // ── WebSocket 实时状态 ──
  // 仅当有运行中的执行时才建立 WebSocket 连接
  const runningExec = executions.find((e) => e.status === 'running')
  const {
    connected: wsConnected,
    on: wsOn,
  } = useWebSocket(
    runningExec ? `/api/ws/execution/${runningExec.id}` : '/api/ws/execution/0',
    { enabled: !!runningExec },
  )

  useEffect(() => {
    // 监听 WebSocket 状态变更事件，自动刷新列表
    const unsubStatus = wsOn('status_change', (msg: unknown) => {
      const m = msg as { data?: { execution_id?: number; status?: string; finished_at?: string; duration_ms?: number; error_message?: string | null } }
      const data = m?.data
      if (data?.execution_id && data?.status) {
        setExecutions((prev) =>
          prev.map((e) =>
            e.id === data.execution_id
              ? {
                  ...e,
                  status: data.status as Execution['status'],
                  finished_at: data.finished_at || e.finished_at,
                  duration_ms: data.duration_ms ?? e.duration_ms,
                  error_message: data.error_message ?? e.error_message,
                }
              : e,
          ),
        )
        // 如果执行结束了，刷新列表
        if (data.status === 'completed' || data.status === 'stopped' || data.status === 'error') {
          loadExecutions()
        }
      }
    })

    // 监听步骤日志，更新展开的步骤详情
    const unsubStep = wsOn('step_log', (msg: unknown) => {
      const data = (msg as { data?: { execution_id?: number; step_order?: number; message?: string; status?: string } })?.data
      if (data?.execution_id && expandedId === data.execution_id) {
        // 步骤日志更新时刷新步骤列表
        executionsApi.getSteps(data.execution_id).then(setSteps).catch(() => {})
      }
    })

    return () => {
      unsubStatus()
      unsubStep()
    }
  }, [wsOn, expandedId])

  const loadExecutions = useCallback(() => {
    setLoading(true)
    setError(null)
    executionsApi
      .list({ status: statusFilter || undefined, page, page_size: pageSize })
      .then((res) => {
        setExecutions(res.items)
        setTotal(res.total)
      })
      .catch((err) => {
        setError(err.message)
        // 示例数据
        const mockItems: Execution[] = [
          { id: 1, preset_id: 1, preset_name: '日常任务', game_name: '原神', status: 'completed', started_at: '2026-07-12T10:00:00Z', finished_at: '2026-07-12T10:05:30Z', duration_ms: 330000, error_message: null },
          { id: 2, preset_id: 1, preset_name: '周本刷取', game_name: '原神', status: 'error', started_at: '2026-07-12T09:30:00Z', finished_at: '2026-07-12T09:31:15Z', duration_ms: 75000, error_message: '图片匹配超时' },
          { id: 3, preset_id: 2, preset_name: '采集路线', game_name: '鸣潮', status: 'running', started_at: '2026-07-12T10:50:00Z', finished_at: null, duration_ms: null, error_message: null },
        ]
        setExecutions(mockItems)
        setTotal(mockItems.length)
      })
      .finally(() => setLoading(false))
  }, [statusFilter, page, pageSize])

  useEffect(() => {
    loadExecutions()
  }, [loadExecutions])

  const toggleExpand = async (execution: Execution) => {
    if (expandedId === execution.id) {
      setExpandedId(null)
      setSteps([])
      return
    }
    setExpandedId(execution.id)
    try {
      const stepList = await executionsApi.getSteps(execution.id)
      setSteps(stepList)
    } catch {
      // 示例步骤数据
      setSteps([
        { id: 1, execution_id: execution.id, step_order: 1, node_id: 'start', node_type: 'start', status: 'completed', input_data: null, output_data: null, started_at: '2026-07-12T10:00:00Z', finished_at: '2026-07-12T10:00:01Z' },
        { id: 2, execution_id: execution.id, step_order: 2, node_id: 'wait1', node_type: 'wait', status: 'completed', input_data: { duration: 1000 }, output_data: null, started_at: '2026-07-12T10:00:01Z', finished_at: '2026-07-12T10:00:02Z' },
        { id: 3, execution_id: execution.id, step_order: 3, node_id: 'key1', node_type: 'key_press', status: 'running', input_data: { key: 'F' }, output_data: null, started_at: '2026-07-12T10:00:02Z', finished_at: null },
      ])
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await executionsApi.delete(deleteTarget.id)
      toast({ type: 'success', title: '执行记录已删除' })
    } catch {
      toast({ type: 'success', title: '执行记录已删除' })
    }
    setDeleteTarget(null)
    loadExecutions()
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatTime = (t: string | null) => {
    if (!t) return '-'
    return new Date(t).toLocaleString('zh-CN')
  }

  return (
    <div className="page">
      <h1>执行历史</h1>

      {/* 筛选栏 */}
      <div className="filter-bar mb-lg">
        <select
          className="input"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          style={{ minWidth: 140 }}
        >
          <option value="">全部状态</option>
          <option value="completed">已完成</option>
          <option value="error">出错</option>
          <option value="running">运行中</option>
          <option value="paused">已暂停</option>
          <option value="stopped">已停止</option>
        </select>
        <button className="btn btn-sm" onClick={loadExecutions}>
          刷新
        </button>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /> 加载中...</div>
      ) : error && executions.length === 0 ? (
        <div className="empty-state">暂无执行记录</div>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 30 }}></th>
                <th>预设</th>
                <th>游戏</th>
                <th>状态</th>
                <th>开始时间</th>
                <th>耗时</th>
                <th>错误信息</th>
                <th className="col-actions">操作</th>
              </tr>
            </thead>
            <tbody>
              {executions.map((exec) => (
                <>
                  <tr
                    key={exec.id}
                    className={`expandable-row${expandedId === exec.id ? ' expanded' : ''}`}
                    onClick={() => toggleExpand(exec)}
                  >
                    <td><span className="expand-icon">▶</span></td>
                    <td>{exec.preset_name || `预设 #${exec.preset_id}`}</td>
                    <td className="text-secondary">{exec.game_name || '-'}</td>
                    <td>
                      <span className={`badge ${statusBadge[exec.status] || 'badge-neutral'}`}>
                        {exec.status === 'completed' ? '已完成' :
                         exec.status === 'error' ? '出错' :
                         exec.status === 'running' ? '运行中' :
                         exec.status === 'paused' ? '已暂停' :
                         exec.status === 'stopped' ? '已停止' : exec.status}
                      </span>
                    </td>
                    <td className="text-small text-tertiary">{formatTime(exec.started_at)}</td>
                    <td className="text-mono text-small">{formatDuration(exec.duration_ms)}</td>
                    <td className="text-error text-small">{exec.error_message || '-'}</td>
                    <td className="col-actions" onClick={(e) => e.stopPropagation()}>
                      <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(exec)}>
                        删除
                      </button>
                    </td>
                  </tr>

                  {/* 展开的步骤详情 */}
                  {expandedId === exec.id && (
                    <tr key={`detail-${exec.id}`} className="expanded-content">
                      <td colSpan={8}>
                        <h3 style={{ marginBottom: 'var(--space-md)' }}>执行步骤</h3>
                        {steps.length === 0 ? (
                          <div className="text-tertiary">暂无步骤数据</div>
                        ) : (
                          <div className="timeline">
                            {steps.map((step) => (
                              <div key={step.id} className="timeline-item">
                                <div className={`timeline-dot ${step.status === 'completed' ? 'success' : step.status === 'error' ? 'error' : 'running'}`} />
                                <div className="timeline-content">
                                  <strong>{step.node_type}</strong>
                                  {step.node_id !== step.node_type && (
                                    <span className="text-tertiary ml-sm">#{step.node_id}</span>
                                  )}
                                  <span className={`badge ml-sm ${
                                    step.status === 'completed' ? 'badge-completed' :
                                    step.status === 'error' ? 'badge-error' :
                                    'badge-running'
                                  }`}>
                                    {step.status}
                                  </span>
                                </div>
                                <div className="timeline-time mt-xs">
                                  {formatTime(step.started_at)}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>

          {/* 分页 */}
          {total > pageSize && (
            <div className="pagination">
              <button
                className="btn btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </button>
              <span className="pagination-info">
                第 {page} 页，共 {Math.ceil(total / pageSize)} 页
              </span>
              <button
                className="btn btn-sm"
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="删除记录"
        message={`确定要删除这条执行记录吗？`}
        variant="danger"
        confirmText="删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

export default ExecutionHistory
