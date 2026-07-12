import { useParams } from 'react-router-dom'

function FlowEditor() {
  const { presetId } = useParams<{ presetId: string }>()

  return (
    <div className="page">
      <h1>流程编辑器</h1>
      <div className="flow-placeholder">
        <div className="flow-panel flow-panel-left">
          <h3>节点面板</h3>
          <p className="text-secondary">拖拽节点到画布</p>
        </div>
        <div className="flow-canvas">
          <div className="empty-state">流程图画布（预设 ID: {presetId}）</div>
        </div>
        <div className="flow-panel flow-panel-right">
          <h3>属性面板</h3>
          <p className="text-secondary">选择节点查看属性</p>
        </div>
      </div>
    </div>
  )
}

export default FlowEditor
