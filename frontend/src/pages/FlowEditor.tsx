import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useToast } from '../components/ui/Toast'

interface NodeCategory {
  name: string
  icon: string
  nodes: { type: string; label: string; icon: string }[]
}

const NODE_CATEGORIES: NodeCategory[] = [
  {
    name: '流程控制',
    icon: '🔀',
    nodes: [
      { type: 'start', label: '开始', icon: '▶' },
      { type: 'end', label: '结束', icon: '■' },
      { type: 'wait', label: '等待', icon: '⏳' },
      { type: 'condition', label: '条件判断', icon: '❓' },
      { type: 'loop', label: '循环', icon: '↻' },
    ],
  },
  {
    name: '键盘操作',
    icon: '⌨️',
    nodes: [
      { type: 'key_press', label: '按键', icon: '⌨' },
      { type: 'key_combo', label: '组合键', icon: '⇧' },
      { type: 'key_hold', label: '长按', icon: '⏱' },
    ],
  },
  {
    name: '鼠标操作',
    icon: '🖱️',
    nodes: [
      { type: 'mouse_click', label: '点击', icon: '🖱' },
      { type: 'mouse_dblclick', label: '双击', icon: '🖱' },
      { type: 'mouse_drag', label: '拖拽', icon: '↗' },
      { type: 'mouse_scroll', label: '滚动', icon: '⬇' },
    ],
  },
  {
    name: '视觉识别',
    icon: '👁️',
    nodes: [
      { type: 'ocr_recognize', label: 'OCR 识别', icon: '🔍' },
      { type: 'template_match', label: '图片匹配', icon: '🖼' },
      { type: 'screenshot', label: '截图', icon: '📷' },
    ],
  },
  {
    name: '数据操作',
    icon: '📦',
    nodes: [
      { type: 'variable_set', label: '变量赋值', icon: '📝' },
      { type: 'text_output', label: '文本输出', icon: '💬' },
    ],
  },
]

interface CanvasNode {
  id: string
  type: string
  label: string
  x: number
  y: number
}

let nodeCounter = 0

// 节点类型 → 颜色映射
const NODE_COLORS: Record<string, string> = {
  start: '#10b981',
  end: '#ef4444',
  wait: '#f59e0b',
  condition: '#3b82f6',
  loop: '#8b5cf6',
  key_press: '#6366f1',
  key_combo: '#6366f1',
  key_hold: '#6366f1',
  mouse_click: '#ec4899',
  mouse_dblclick: '#ec4899',
  mouse_drag: '#ec4899',
  mouse_scroll: '#ec4899',
  ocr_recognize: '#14b8a6',
  template_match: '#14b8a6',
  screenshot: '#14b8a6',
  variable_set: '#f97316',
  text_output: '#f97316',
}

function FlowEditor() {
  const { presetId } = useParams<{ presetId: string }>()
  const { toast } = useToast()
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([
    { id: 'n_1', type: 'start', label: '开始', x: 300, y: 40 },
    { id: 'n_2', type: 'wait', label: '等待 1s', x: 300, y: 160 },
    { id: 'n_3', type: 'key_press', label: '按键 A', x: 300, y: 280 },
    { id: 'n_4', type: 'end', label: '结束', x: 300, y: 400 },
  ])
  const [selectedNode, setSelectedNode] = useState<CanvasNode | null>(null)
  const [zoom, setZoom] = useState(1)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const data = e.dataTransfer.getData('text/plain')
    if (!data) return
    const { type, label } = JSON.parse(data)
    nodeCounter++
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left - 75) / zoom
    const y = (e.clientY - rect.top - 20) / zoom
    const newNode: CanvasNode = { id: `n_${Date.now()}`, type, label, x, y }
    setCanvasNodes((prev) => [...prev, newNode])
    toast({ type: 'info', title: `已添加节点: ${label}` })
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleNodeDragStart = (e: React.DragEvent, node: CanvasNode) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: node.type, label: node.label }))
  }

  const handleNodeDragEnd = (_e: React.DragEvent) => {
    // TODO: 实现精确拖拽位置映射
  }

  const handleSave = () => {
    toast({ type: 'success', title: '流程已保存' })
  }

  const handleExecute = () => {
    toast({ type: 'info', title: '开始执行流程', description: `预设 #${presetId}` })
  }

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.1, 2))
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.1, 0.5))
  const handleFit = () => setZoom(1)

  return (
    <div className="page page-flow">
      {/* 工具栏 */}
      <div className="flow-toolbar">
        <div className="flex items-center gap-sm flex-1">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/></svg>
          <span className="text-secondary text-small" style={{ fontWeight: 500 }}>流程编辑器</span>
          {presetId && <span className="badge badge-neutral">预设 #{presetId}</span>}
        </div>
        <button className="btn btn-sm btn-primary" onClick={handleSave}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          保存
        </button>
        <button className="btn btn-sm" onClick={handleExecute}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          执行
        </button>
        <div className="flex items-center gap-sm ml-auto">
          <button className="btn btn-sm btn-icon" onClick={handleZoomOut} title="缩小">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
          </button>
          <span className="zoom-level">{Math.round(zoom * 100)}%</span>
          <button className="btn btn-sm btn-icon" onClick={handleZoomIn} title="放大">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/><line x1="11" y1="8" x2="11" y2="14"/></svg>
          </button>
          <button className="btn btn-sm btn-icon" onClick={handleFit} title="适应画布">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
          </button>
        </div>
      </div>

      {/* 三栏布局 */}
      <div className="flow-editor flow-editor-viewport">
        {/* 左侧节点面板 */}
        <div className="flow-panel">
          <div className="flow-panel-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            节点面板
          </div>
          {NODE_CATEGORIES.map((cat) => (
            <div className="node-category" key={cat.name}>
              <div className="node-category-title">
                <span>{cat.icon}</span>
                <span>{cat.name}</span>
              </div>
              {cat.nodes.map((node) => (
                <div
                  key={node.type}
                  className="node-item"
                  draggable
                  onDragStart={(e) =>
                    e.dataTransfer.setData(
                      'text/plain',
                      JSON.stringify({ type: node.type, label: node.label }),
                    )
                  }
                >
                  <span className="node-item-dot" style={{ background: NODE_COLORS[node.type] || 'var(--text-tertiary)' }} />
                  <span className="node-item-icon">{node.icon}</span>
                  <span>{node.label}</span>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* 中间画布 */}
        <div className="flow-canvas" onDrop={handleDrop} onDragOver={handleDragOver}>
          <svg
            width="100%"
            height="100%"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
          >
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.2)" />
              </marker>
              {/* 节点阴影滤镜 */}
              <filter id="node-shadow">
                <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.4)" />
              </filter>
              <filter id="node-shadow-selected">
                <feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="rgba(79,70,229,0.5)" />
              </filter>
              {/* 节点渐变色 */}
              <linearGradient id="node-bg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#222145" />
                <stop offset="100%" stopColor="#1a1932" />
              </linearGradient>
            </defs>

            {/* 连线 */}
            {canvasNodes.slice(0, -1).map((node, i) => {
              const next = canvasNodes[i + 1]
              const isSelected = selectedNode?.id === node.id || selectedNode?.id === next.id
              return (
                <g key={`line-${node.id}`}>
                  <line
                    x1={node.x + 75}
                    y1={node.y + 52}
                    x2={next.x + 75}
                    y2={next.y}
                    stroke={isSelected ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.12)'}
                    strokeWidth={isSelected ? 2.5 : 2}
                    strokeDasharray={isSelected ? 'none' : 'none'}
                    markerEnd="url(#arrowhead)"
                  />
                </g>
              )
            })}

            {/* 节点 */}
            {canvasNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id
              const nodeColor = NODE_COLORS[node.type] || 'var(--color-primary)'
              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* 节点主体背景 */}
                  <rect
                    x={node.x}
                    y={node.y}
                    width={150}
                    height={52}
                    rx={10}
                    ry={10}
                    fill="url(#node-bg)"
                    stroke={isSelected ? 'var(--color-primary)' : 'var(--border-default)'}
                    strokeWidth={isSelected ? 2 : 1}
                    filter={isSelected ? 'url(#node-shadow-selected)' : 'url(#node-shadow)'}
                  />
                  {/* 类型色顶部条 */}
                  <rect
                    x={node.x + 2}
                    y={node.y + 2}
                    width={146}
                    height={3}
                    rx={1.5}
                    ry={1.5}
                    fill={nodeColor}
                  />
                  {/* 节点图标 */}
                  <text
                    x={node.x + 18}
                    y={node.y + 32}
                    textAnchor="middle"
                    fontSize="14"
                  >
                    {NODE_CATEGORIES.flatMap(c => c.nodes).find(n => n.type === node.type)?.icon || '⚙'}
                  </text>
                  {/* 节点标签 */}
                  <text
                    x={node.x + 75}
                    y={node.y + 20}
                    textAnchor="middle"
                    fill="var(--text-secondary)"
                    fontSize="10"
                    fontFamily="var(--font-sans)"
                    letterSpacing="0.5"
                    style={{ textTransform: 'uppercase' }}
                  >
                    {node.type.replace('_', ' ')}
                  </text>
                  <text
                    x={node.x + 75}
                    y={node.y + 37}
                    textAnchor="middle"
                    fill="var(--text-primary)"
                    fontSize="13"
                    fontWeight="600"
                    fontFamily="var(--font-sans)"
                  >
                    {node.label.length > 16 ? node.label.slice(0, 16) + '…' : node.label}
                  </text>
                  {/* 选中边框指示器 */}
                  {isSelected && (
                    <rect
                      x={node.x - 3}
                      y={node.y - 3}
                      width={156}
                      height={58}
                      rx={12}
                      ry={12}
                      fill="none"
                      stroke="var(--color-primary)"
                      strokeWidth={2}
                      opacity={0.5}
                      strokeDasharray="4 3"
                    />
                  )}
                </g>
              )
            })}

            {/* 空画布提示 */}
            {canvasNodes.length === 0 && (
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                fill="var(--text-tertiary)"
                fontSize="14"
                fontFamily="var(--font-sans)"
              >
                从左侧拖拽节点到画布
              </text>
            )}
          </svg>
        </div>

        {/* 右侧属性面板 */}
        <div className="flow-property-panel">
          <div className="flow-panel-header" style={{ padding: '0 0 var(--space-md)', borderBottom: '1px solid var(--border-default)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            节点属性
          </div>
          {selectedNode ? (
            <div className="property-content">
              <div className="form-group">
                <label className="form-label">类型</label>
                <div className="flex items-center gap-sm">
                  <span
                    className="node-item-dot"
                    style={{ background: NODE_COLORS[selectedNode.type] || 'var(--text-tertiary)', width: 8, height: 8, borderRadius: '50%', flexShrink: 0 }}
                  />
                  <input className="input input-sm" value={selectedNode.type} readOnly />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">标签</label>
                <input className="input input-sm" value={selectedNode.label} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">节点 ID</label>
                <input className="input input-sm text-mono" value={selectedNode.id} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">位置</label>
                <div className="form-row" style={{ gap: 'var(--space-sm)' }}>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="form-label text-small text-tertiary">X</label>
                    <input className="input input-sm text-mono" value={Math.round(selectedNode.x)} readOnly />
                  </div>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="form-label text-small text-tertiary">Y</label>
                    <input className="input input-sm text-mono" value={Math.round(selectedNode.y)} readOnly />
                  </div>
                </div>
              </div>
              <div className="node-delete-section">
                <button
                  className="btn btn-sm btn-block"
                  style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}
                  onClick={() => {
                    setCanvasNodes((prev) => prev.filter((n) => n.id !== selectedNode.id))
                    setSelectedNode(null)
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                  删除节点
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ border: 'none', background: 'transparent', padding: 'var(--space-xl) 0' }}>
              <div className="text-tertiary" style={{ textAlign: 'center' }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ marginBottom: 12, opacity: 0.4 }}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33"/><path d="M9 19.4a1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 004.68 15"/><path d="M4.68 9A1.65 1.65 0 003 7.4V3a2 2 0 014 0v.09"/><path d="M15 4.68a1.65 1.65 0 001.51-1H21a2 2 0 010 4h-.09"/></svg>
                <div style={{ fontSize: 'var(--text-body)', marginBottom: 4 }}>选中节点查看属性</div>
                <div style={{ fontSize: 'var(--text-small)' }}>点击画布上的节点即可编辑</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FlowEditor
