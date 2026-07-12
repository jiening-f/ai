function Settings() {
  return (
    <div className="page">
      <h1>系统设置</h1>
      <div className="section">
        <h2>通用设置</h2>
        <div className="form-group">
          <label className="form-label">后端地址</label>
          <input className="input" type="text" defaultValue="http://127.0.0.1:8765" readOnly />
        </div>
        <div className="form-group">
          <label className="form-label">语言</label>
          <select className="input">
            <option value="zh-CN">简体中文</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
    </div>
  )
}

export default Settings
