import { NavLink } from 'react-router-dom'

interface NavItem {
  path: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/games', label: '游戏管理', icon: '🎮' },
  { path: '/presets/0', label: '预设编辑', icon: '📝' },
  { path: '/flow/0', label: '流程编辑', icon: '🔀' },
  { path: '/history', label: '执行历史', icon: '📋' },
  { path: '/plugins', label: '插件管理', icon: '🧩' },
  { path: '/settings', label: '系统设置', icon: '⚙️' },
]

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">全能脚本</div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' active' : ''}`
            }
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">v0.1.0</div>
    </aside>
  )
}

export default Sidebar
