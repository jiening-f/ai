import { useParams } from 'react-router-dom'

function PresetEditor() {
  const { gameId } = useParams<{ gameId: string }>()

  return (
    <div className="page">
      <div className="page-header">
        <h1>预设编辑</h1>
        <button className="btn btn-primary">新建预设</button>
      </div>
      <div className="empty-state">
        暂无预设配置（游戏 ID: {gameId}）
      </div>
    </div>
  )
}

export default PresetEditor
