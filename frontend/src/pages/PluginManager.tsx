function PluginManager() {
  return (
    <div className="page">
      <div className="page-header">
        <h1>插件管理</h1>
        <button className="btn btn-primary">安装插件</button>
      </div>
      <div className="card-grid">
        <div className="card card-plugin">
          <div className="card-title">暂无插件</div>
          <div className="text-secondary">尚未安装任何插件</div>
        </div>
      </div>
    </div>
  )
}

export default PluginManager
