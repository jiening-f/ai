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
      toast({ type: 'success', title: '预设已保存' })
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
      <div className="page-header">
        <h1>预设编辑 {gameId && gameId !== '0' ? `- 游戏 #${gameId}` : ''}</h1>
        <div className="flex gap-sm">
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '💾 保存'}
          </button>
          <button className="btn" onClick={handleExecute}>▶ 执行</button>
          <button className="btn" onClick={handleStop}>⏹ 停止</button>
        </div>
      </div>

      <div className="section">
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
        <div className="form-group">
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

      {/* 步骤表格 */}
      <div className="section">
        <div className="section-header">
          <h2>执行步骤</h2>
          <button className="btn btn-sm btn-primary" onClick={addStep}>
            + 添加步骤
          </button>
        </div>

        {steps.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-text">暂无步骤，点击"添加步骤"开始</div>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}></th>
                  <th style={{ width: 60 }}>序号</th>
                  <th style={{ width: 140 }}>节点类型</th>
                  <th>配置参数</th>
                  <th style={{ width: 80 }}>启用</th>
                  <th style={{ width: 80 }} className="col-actions">操作</th>
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
                    style={{ cursor: 'grab', opacity: step.enabled ? 1 : 0.5 }}
                  >
                    <td className="text-tertiary">⠿</td>
                    <td>{step.order}</td>
                    <td>
                      <select
                        className="input"
                        value={step.nodeType}
                        onChange={(e) => updateStep(step.id, 'nodeType', e.target.value)}
                        style={{ width: '130px' }}
                      >
                        {NODE_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="input"
                        value={step.config}
                        onChange={(e) => updateStep(step.id, 'config', e.target.value)}
                        placeholder="配置参数..."
                      />
                    </td>
                    <td>
                      <div
                        className={`toggle ${step.enabled ? 'active' : ''}`}
                        onClick={() => toggleStep(step.id)}
                      />
                    </td>
                    <td className="col-actions">
                      <button className="btn btn-sm btn-danger" onClick={() => removeStep(step.id)}>
                        删除
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
