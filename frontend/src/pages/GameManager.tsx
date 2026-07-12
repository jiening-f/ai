function GameManager() {
  return (
    <div className="page">
      <div className="page-header">
        <h1>游戏管理</h1>
        <button className="btn btn-primary">添加游戏</button>
      </div>
      <div className="empty-state">
        暂无游戏配置，点击"添加游戏"开始
      </div>
    </div>
  )
}

export default GameManager
