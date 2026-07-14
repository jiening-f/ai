## 任务：UI 设计规范

### 目标
制定完整的设计规范文档，为前端开发提供统一的设计语言。

### 工作目录
`ui-design/`

### 要求

1. **设计 Token (`design-tokens.md`)**
   - 颜色系统（暗色主题为主）
     - 背景色：页面背景、卡片背景、输入框背景
     - 文字色：主文字、次要文字、禁用文字
     - 强调色：主色（蓝紫）、成功色（绿）、警告色（黄）、错误色（红）
     - 边框色
   - 间距系统（4px 基准）：xs(4) / sm(8) / md(16) / lg(24) / xl(32) / 2xl(48)
   - 字体系统：字体族、字号层级（h1/h2/h3/body/small）
   - 圆角：sm(4) / md(8) / lg(12)
   - 阴影层级

2. **组件规格 (`component-specs/`)**
   - 每个组件一个 markdown 文件，描述：
     - 组件名称与用途
     - 视觉样式描述
     - 交互状态（默认/悬停/激活/禁用）
     - 尺寸变体（如有）
   - 至少覆盖以下组件：
     - Button（按钮）
     - Input（输入框）
     - Select（下拉选择）
     - Card（卡片）
     - Modal（弹窗）
     - Table（表格）
     - Tabs（标签页）
     - Badge（标签）
     - Sidebar（侧边栏 — 导航菜单）
     - Toast（通知）

3. **页面布局描述 (`page-mockups/`)**
   - 7 个核心页面的布局描述（ASCII 线框图即可）：
     - Dashboard — 仪表盘（状态卡片 + 快捷操作 + 最近执行）
     - GameManager — 游戏管理（游戏卡片列表 + 添加按钮）
     - PresetEditor — 预设编辑（表格行编辑 + 启用/禁用开关）
     - FlowEditor — 流程编辑器（左侧节点面板 + 中间画布 + 右侧属性面板）
     - ExecutionHistory — 执行历史（筛选栏 + 表格列表）
     - PluginManager — 插件管理（插件卡片网格 + 安装/卸载按钮）
     - Settings — 系统设置（标签页分组 + 表单控件）

4. **产出文件**
   ```
   ui-design/
   ├── design-tokens.md
   ├── component-specs/
   │   ├── button.md
   │   ├── input.md
   │   ├── select.md
   │   ├── card.md
   │   ├── modal.md
   │   ├── table.md
   │   ├── tabs.md
   │   ├── badge.md
   │   ├── sidebar.md
   │   └── toast.md
   └── page-mockups/
       ├── dashboard.md
       ├── game-manager.md
       ├── preset-editor.md
       ├── flow-editor.md
       ├── execution-history.md
       ├── plugin-manager.md
       └── settings.md
   ```

### 参考架构
详见 `docs/architecture.md` 第三节目录结构。
