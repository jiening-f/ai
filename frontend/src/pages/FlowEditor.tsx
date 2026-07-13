import { useState, useRef } from 'react'
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
      { type: 'end', label: '结束', icon: '⏹' },
      { type: 'wait', label: '等待', icon: '⏳' },
      { type: 'condition', label: '条件判断', icon: '❓' },
      { type: 'loop', label: '循环', icon: '🔄' },
    ],
  },
  {
    name: '键盘操作',
    icon: '⌨️',
    nodes: [
      { type: 'key_press', label: '按键', icon: '⌨' },
      { type: 'key_combo', label: '组合键', icon: '🔣' },
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

function FlowEditor() {
  const { presetId } = useParams<{ presetId: string }>()
  const { toast } = useToast()
  const nodeCounterRef = useRef(0)

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
    nodeCounterRef.current++
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
    <div className="page" style={{ padding: 0 }}>
      {/* 工具栏 */}
      <div className="flow-toolbar">
        <button className="btn btn-sm btn-primary" onClick={handleSave}>
          💾 保存
        </button>
        <button className="btn btn-sm" onClick={handleExecute}>
          ▶ 执行
        </button>
        <span style={{ flex: 1 }} />
        <button className="btn btn-sm" onClick={handleZoomOut}>−</button>
        <span className="text-secondary text-small">{Math.round(zoom * 100)}%</span>
        <button className="btn btn-sm" onClick={handleZoomIn}>+</button>
        <button className="btn btn-sm" onClick={handleFit}>⊡</button>
      </div>

      {/* 三栏布局 */}
      <div className="flow-editor" style={{ height: 'calc(100vh - 56px - 48px)' }}>
        {/* 左侧节点面板 */}
        <div className="flow-panel">
          {NODE_CATEGORIES.map((cat) => (
            <div className="node-category" key={cat.name}>
              <div className="node-category-title">
                {cat.icon} {cat.name}
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
                  <span className="node-item-icon">{node.icon}</span>
                  {node.label}
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
            {/* 连线 */}
            {canvasNodes.slice(0, -1).map((node, i) => {
              const next = canvasNodes[i + 1]
              return (
                <line
                  key={`line-${node.id}`}
                  x1={node.x + 75}
                  y1={node.y + 24}
                  x2={next.x + 75}
                  y2={next.y}
                  stroke="rgba(255,255,255,0.15)"
                  strokeWidth={2}
                  markerEnd="url(#arrowhead)"
                />
              )
            })}
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="rgba(255,255,255,0.15)" />
              </marker>
            </defs>

            {/* 节点 */}
            {canvasNodes.map((node) => (
              <g
                key={node.id}
                onClick={() => setSelectedNode(node)}
                style={{ cursor: 'pointer' }}
              >
                <rect
                  x={node.x}
                  y={node.y}
                  width={150}
                  height={48}
                  rx={8}
                  ry={8}
                  fill={selectedNode?.id === node.id ? '#4f46e5' : '#1a1932'}
                  stroke={selectedNode?.id === node.id ? '#6366f1' : 'rgba(255,255,255,0.08)'}
                  strokeWidth={selectedNode?.id === node.id ? 2 : 1}
                />
                <text
                  x={node.x + 75}
                  y={node.y + 28}
                  textAnchor="middle"
                  fill="#f1f5f9"
                  fontSize="13"
                  fontFamily="Inter, sans-serif"
                >
                  {node.label}
                </text>
              </g>
            ))}

            {/* 空画布提示 */}
            {canvasNodes.length === 0 && (
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                fill="#64748b"
                fontSize="14"
              >
                从左侧拖拽节点到画布
              </text>
            )}
          </svg>
        </div>

        {/* 右侧属性面板 */}
        <div className="flow-property-panel">
          {selectedNode ? (
            <>
              <h3 style={{ marginBottom: 'var(--space-md)' }}>节点属性</h3>
              <div className="form-group">
                <label className="form-label">类型</label>
                <input className="input" value={selectedNode.type} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">标签</label>
                <input className="input" value={selectedNode.label} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">节点 ID</label>
                <input className="input text-mono" value={selectedNode.id} readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">位置</label>
                <div className="form-row">
                  <input className="input" value={`X: ${Math.round(selectedNode.x)}`} readOnly />
                  <input className="input" value={`Y: ${Math.round(selectedNode.y)}`} readOnly />
                </div>
              </div>
              <div className="mt-lg">
                <button className="btn btn-danger btn-sm" onClick={() => {
                  setCanvasNodes((prev) => prev.filter((n) => n.id !== selectedNode.id))
                  setSelectedNode(null)
                }}>
                  删除节点
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ border: 'none', background: 'transparent' }}>
              <div className="text-secondary" style={{ textAlign: 'center', padding: 'var(--space-xl) 0' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>👆</div>
                选中节点查看属性
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FlowEditor
