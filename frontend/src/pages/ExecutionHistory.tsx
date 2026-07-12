function ExecutionHistory() {
  return (
    <div className="page">
      <div className="page-header">
        <h1>执行历史</h1>
        <div className="filter-bar">
          <select className="input">
            <option value="">全部状态</option>
            <option value="completed">已完成</option>
            <option value="error">出错</option>
            <option value="stopped">已停止</option>
          </select>
        </div>
      </div>
      <div className="empty-state">暂无执行记录</div>
    </div>
  )
}

export default ExecutionHistory
