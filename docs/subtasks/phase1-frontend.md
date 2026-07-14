## 任务：前端项目骨架搭建

### 目标
搭建 React + TypeScript + Vite 前端项目，包含基础路由和布局框架。

### 工作目录
`frontend/`

### 要求

1. **技术栈**
   - React 18 + TypeScript
   - Vite 构建工具
   - React Router v6（路由）
   - Zustand（状态管理）
   - TailwindCSS 或 CSS Modules（样式）

2. **项目结构**
   ```
   frontend/
   ├── src/
   │   ├── main.tsx           # 入口
   │   ├── App.tsx             # 路由配置
   │   ├── api/
   │   │   └── client.ts       # fetch 封装（base URL 可配置）
   │   ├── pages/
   │   │   ├── Dashboard.tsx   # 仪表盘（占位页面）
   │   │   ├── GameManager.tsx # 游戏管理（占位页面）
   │   │   ├── PresetEditor.tsx # 预设编辑（占位页面）
   │   │   ├── FlowEditor.tsx  # 流程编辑器（占位页面）
   │   │   ├── ExecutionHistory.tsx # 执行历史（占位页面）
   │   │   ├── PluginManager.tsx # 插件管理（占位页面）
   │   │   └── Settings.tsx    # 系统设置（占位页面）
   │   ├── components/
   │   │   └── layout/
   │   │       ├── Sidebar.tsx   # 侧边导航栏
   │   │       └── Layout.tsx    # 主布局（侧边栏 + 内容区）
   │   ├── hooks/
   │   │   └── useApi.ts        # API 调用 Hook
   │   └── styles/
   │       └── global.css       # 全局样式 + 暗色主题变量
   ├── index.html
   ├── package.json
   ├── vite.config.ts
   └── tsconfig.json
   ```

3. **路由设计**
   | 路径 | 页面组件 |
   |------|---------|
   | / | Dashboard |
   | /games | GameManager |
   | /presets/:gameId | PresetEditor |
   | /flow/:presetId | FlowEditor |
   | /history | ExecutionHistory |
   | /plugins | PluginManager |
   | /settings | Settings |

4. **布局**
   - 左侧固定侧边栏（深色背景，导航菜单）
   - 右侧内容区
   - 暗色主题（深灰背景 #1a1a2e，亮色文字）

5. **验证**
   - `cd frontend && npm install && npm run dev` 能启动
   - 浏览器访问能看到侧边栏 + 仪表盘占位内容
   - 所有 7 个页面路由可切换

### 参考架构
详见 `docs/architecture.md` 第三节目录结构和第八节通信协议。
