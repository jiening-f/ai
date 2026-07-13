import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { presetsApi, Preset, PresetFormData } from '../api/presets'
import { useToast } from '../components/ui/Toast'

interface StepItem {
  id: string
  order: number
  nodeType: string
  config: string
  enabled: boolean
}

const NODE_TYPE_OPTIONS = [
  { value: 'start', label: '开始' },
  { value: 'end', label: '结束' },
  { value: 'wait', label: '等待' },
  { value: 'condition', label: '条件判断' },
  { value: 'loop', label: '循环' },
  { value: 'key_press', label: '按键' },
  { value: 'key_combo', label: '组合键' },
  { value: 'mouse_click', label: '鼠标点击' },
  { value: 'mouse_dblclick', label: '鼠标双击' },
  { value: 'ocr_recognize', label: 'OCR 识别' },
  { value: 'template_match', label: '图片匹配' },
  { value: 'screenshot', label: '截图' },
  { value: 'text_output', label: '文本输出' },
]

const NODE_TYPE_ICONS: Record<string, string> = {
  start: '▶', end: '■', wait: '⏳',
  condition: '❓', loop: '↻',
  key_press: '⌨', key_combo: '⇧',
  mouse_click: '🖱', mouse_dblclick: '🖱',
  ocr_recognize: '🔍', template_match: '🖼',
  screenshot: '📷', text_output: '💬',
}

let stepCounter = 0

function PresetEditor() {
  const { gameId } = useParams<{ gameId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [presets, setPresets] = useState<Preset[]>([])
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(null)
  const [loading, setLoading] = useState(true)

  // 编辑态
  const [presetName, setPresetName] = useState('')
  const [presetDesc, setPresetDesc] = useState('')
  const [steps, setSteps] = useState<StepItem[]>([])
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!gameId || gameId === '0') {
      setLoading(false)
      return
    }
    presetsApi
      .listByGame(Number(gameId))
      .then((list) => {
        setPresets(list)
        if (list.length > 0) selectPreset(list[0])
      })
      .catch(() => {
        // 后端不可用时用空数据
        setPresets([])
      })
      .finally(() => setLoading(false))
  }, [gameId])

  const selectPreset = (preset: Preset) => {
    setSelectedPreset(preset)
    setPresetName(preset.name)
    setPresetDesc(preset.description || '')
    const flow = preset.flow_data as { steps?: StepItem[] } | null
    setSteps(flow?.steps || [])
  }

  const addStep = () => {
    stepCounter++
    setSteps((prev) => [
      ...prev,
      { id: `step_${stepCounter}`, order: prev.length + 1, nodeType: 'wait', config: '', enabled: true },
    ])
  }

  const removeStep = (id: string) => {
    setSteps((prev) => prev.filter((s) => s.id !== id).map((s, i) => ({ ...s, order: i + 1 })))
  }

  const updateStep = (id: string, field: keyof StepItem, value: unknown) => {
    setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, [field]: value } : s)))
  }

  const toggleStep = (id: string) => {
    setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s)))
  }

  const handleDragStart = (index: number) => {
    setDragIndex(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (dragIndex === null || dragIndex === index) return
    setSteps((prev) => {
      const items = [...prev]
      const [moved] = items.splice(dragIndex, 1)
      items.splice(index, 0, moved)
      return items.map((s, i) => ({ ...s, order: i + 1 }))
    })
    setDragIndex(index)
  }

  const handleDrop = () => {
    setDragIndex(null)
  }

  const handleSave = async () => {
    if (!presetName.trim()) {
      toast({ type: 'warning', title: '请输入预设名称' })
      return
    }
    setSaving(true)
    try {
      const data: PresetFormData = {
        name: presetName,
        description: presetDesc,
        flow_data: { steps: steps.map(({ nodeType, config, enabled }) => ({ nodeType, config, enabled })) },
      }
      if (selectedPreset) {
        await presetsApi.update(selectedPreset.id, data)
        toast({ type: 'success', title: '预设已保存' })
      } else {
        await presetsApi.create(Number(gameId || '0'), data)
        toast({ type: 'success', title: '预设已创建' })
      }
    } catch {
      toast({ type: 'error', title: '保存失败', description: '请检查网络连接或稍后重试' })
    }
    setSaving(false)
  }

  const handleExecute = () => {
    toast({ type: 'info', title: '开始执行', description: `正在执行"${presetName}"` })
  }

  const handleStop = () => {
    toast({ type: 'warning', title: '执行已停止' })
  }

  if (loading) {
    return (
      <div className="page">
        <h1>预设编辑</h1>
        <div className="loading"><div className="spinner" /> 加载中...</div>
      </div>
    )
  }

  return (
    <div className="page">
      {/* 页面头部 */}
      <div className="page-header">
        <div>
          <h1 style={{ marginBottom: 4 }}>预设编辑</h1>
          <div className="text-secondary text-small page-subtitle">
            {gameId && gameId !== '0' ? `游戏 #${gameId}` : '选择游戏后编辑预设'}
          </div>
        </div>
        <div className="flex gap-sm">
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            {saving ? '保存中...' : '保存'}
          </button>
          <button className="btn" onClick={handleExecute}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            执行
          </button>
          <button className="btn" onClick={handleStop}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            停止
          </button>
        </div>
      </div>

      {/* 基本信息卡片 */}
      <div className="card-section section">
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <label className="form-label">预设名称</label>
            <input
              className="input"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              placeholder="输入预设名称..."
            />
          </div>
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">描述</label>
          <textarea
            className="input"
            value={presetDesc}
            onChange={(e) => setPresetDesc(e.target.value)}
            placeholder="预设描述（可选）"
            rows={2}
          />
        </div>
      </div>

      {/* 步骤编辑 */}
      <div className="section">
        <div className="section-header">
          <div className="flex items-center gap-sm">
            <h2 style={{ marginBottom: 0 }}>执行步骤</h2>
            <span className="badge badge-info">{steps.length} 项</span>
          </div>
          <button className="btn btn-sm btn-primary" onClick={addStep}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            添加步骤
          </button>
        </div>

        {steps.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon" style={{ fontSize: 40 }}>+</div>
            <div className="empty-state-text">暂无步骤</div>
            <button className="btn btn-sm btn-primary" onClick={addStep}>添加第一条步骤</button>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}></th>
                  <th style={{ width: 52 }}>#</th>
                  <th style={{ width: 140 }}>节点类型</th>
                  <th>配置参数</th>
                  <th style={{ width: 72 }}>启用</th>
                  <th style={{ width: 72 }} className="col-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((step, index) => (
                  <tr
                    key={step.id}
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDrop={handleDrop}
                    className={!step.enabled ? 'row-disabled' : ''}
                    style={{ cursor: 'grab' }}
                  >
                    <td className="cell-drag-handle" title="拖拽排序">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="18" x2="16" y2="18"/></svg>
                    </td>
                    <td><span className="step-order">{step.order}</span></td>
                    <td>
                      <div className="flex items-center gap-sm">
                        <span className="node-type-icon">{NODE_TYPE_ICONS[step.nodeType] || '⚙'}</span>
                        <select
                          className="input input-sm"
                          value={step.nodeType}
                          onChange={(e) => updateStep(step.id, 'nodeType', e.target.value)}
                        >
                          {NODE_TYPE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </td>
                    <td>
                      <input
                        className="input input-sm"
                        value={step.config}
                        onChange={(e) => updateStep(step.id, 'config', e.target.value)}
                        placeholder="配置参数..."
                      />
                    </td>
                    <td>
                      <div
                        className={`toggle ${step.enabled ? 'active' : ''}`}
                        onClick={() => toggleStep(step.id)}
                        role="switch"
                        aria-checked={step.enabled}
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleStep(step.id) }}
                      />
                    </td>
                    <td className="col-actions">
                      <button className="btn btn-sm btn-ghost btn-danger-text" onClick={() => removeStep(step.id)} title="删除步骤">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default PresetEditor
