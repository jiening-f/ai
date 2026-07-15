import { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

interface LayoutProps {
  children: ReactNode
}

/** 路由路径 → 页面标题映射 */
const pageTitles: Record<string, string> = {
  '/': '仪表盘',
  '/games': '游戏管理',
  '/settings': '系统设置',
  '/history': '执行历史',
  '/plugins': '插件管理',
}

function getPageTitle(pathname: string): string {
  if (pageTitles[pathname]) return pageTitles[pathname]
  if (pathname.startsWith('/presets')) return '预设编辑'
  if (pathname.startsWith('/flow')) return '流程编辑'
  return '全能脚本'
}

function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const title = getPageTitle(location.pathname)

  return (
    <div className="app-layout">
      {/* 顶部栏 */}
      <header className="topbar">
        <div className="topbar-title">{title}</div>
{/* TODO: 接入用户系统获取真实头像 */}
        <div className="topbar-user" title="用户">U</div>
      </header>

      {/* 主体：侧边栏 + 内容 */}
      <div className="app-body">
        <Sidebar />
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
