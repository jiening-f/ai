function Dashboard() {
  return (
    <div className="page">
      <h1>仪表盘</h1>
      <div className="card-grid">
        <div className="card">
          <div className="card-title">运行状态</div>
          <div className="card-value">空闲</div>
        </div>
        <div className="card">
          <div className="card-title">预设总数</div>
          <div className="card-value">0</div>
        </div>
        <div className="card">
          <div className="card-title">今日执行</div>
          <div className="card-value">0</div>
        </div>
        <div className="card">
          <div className="card-title">插件数量</div>
          <div className="card-value">0</div>
        </div>
      </div>
      <div className="section">
        <h2>最近执行</h2>
        <div className="empty-state">暂无执行记录</div>
      </div>
    </div>
  )
}

export default Dashboard
