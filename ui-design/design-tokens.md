# 设计 Token

> 为本项目所有 UI 提供统一的设计语言基础。

---

## 1. 颜色系统

### 1.1 主色调

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-primary` | `#4f46e5` | 主品牌色 — 按钮、链接、激活态 |
| `--color-primary-hover` | `#6366f1` | 悬停态 |
| `--color-primary-active` | `#4338ca` | 按下态 |
| `--color-primary-bg` | `rgba(79, 70, 229, 0.12)` | 浅色背景（标签、提示条） |

### 1.2 语义色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-success` | `#10b981` | 成功 / 运行中 |
| `--color-success-bg` | `rgba(16, 185, 129, 0.12)` | 成功浅背景 |
| `--color-warning` | `#f59e0b` | 警告 / 暂停 |
| `--color-warning-bg` | `rgba(245, 158, 11, 0.12)` | 警告浅背景 |
| `--color-error` | `#ef4444` | 错误 / 停止 |
| `--color-error-bg` | `rgba(239, 68, 68, 0.12)` | 错误浅背景 |
| `--color-info` | `#3b82f6` | 信息提示 |

### 1.3 暗色主题

| Token | 值 | 用途 |
|-------|-----|------|
| `--bg-page` | `#0f0e17` | 页面底色 |
| `--bg-card` | `#1a1932` | 卡片 / 面板底色 |
| `--bg-card-hover` | `#222145` | 卡片悬停底色 |
| `--bg-elevated` | `#252348` | 弹窗 / Dropdown |
| `--bg-input` | `#13122b` | 输入框底色 |
| `--bg-sidebar` | `#1e1b2e` | 侧边栏底色 |
| `--bg-topbar` | `#1e1b2e` | 顶部栏底色 |

### 1.4 文字色（暗色）

| Token | 值 | 用途 |
|-------|-----|------|
| `--text-primary` | `#f1f5f9` | 主文字 |
| `--text-secondary` | `#94a3b8` | 次要文字 / 描述 |
| `--text-tertiary` | `#64748b` | 禁用 / 占位符 |
| `--text-inverse` | `#0f0e17` | 亮色背景上的文字 |

### 1.5 边框与分割线

| Token | 值 | 用途 |
|-------|-----|------|
| `--border-default` | `rgba(255, 255, 255, 0.08)` | 卡片边框、分割线 |
| `--border-hover` | `rgba(255, 255, 255, 0.16)` | 输入框悬停边框 |
| `--border-focus` | `#4f46e5` | 输入框聚焦边框 |

### 1.6 亮色主题

| Token | 值 |
|-------|-----|
| `--bg-page-light` | `#f5f5f7` |
| `--bg-card-light` | `#ffffff` |
| `--text-primary-light` | `#1e293b` |
| `--text-secondary-light` | `#64748b` |
| `--border-default-light` | `#e2e8f0` |

---

## 2. 间距系统（4px 基准）

| Token | 值 | 像素 |
|-------|-----|------|
| `--space-xs` | `4px` | 4px |
| `--space-sm` | `8px` | 8px |
| `--space-md` | `16px` | 16px |
| `--space-lg` | `24px` | 24px |
| `--space-xl` | `32px` | 32px |
| `--space-2xl` | `48px` | 48px |
| `--space-3xl` | `64px` | 64px |

> 卡片内边距使用 `--space-lg`，列表项间距使用 `--space-md`，大区块间距使用 `--space-2xl`。

---

## 3. 字体系统

### 3.1 字体族

| Token | 值 |
|-------|-----|
| `--font-sans` | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` |
| `--font-mono` | `'JetBrains Mono', 'Fira Code', 'Consolas', monospace` |

### 3.2 字号层级

| Token | 值 | 行高 | 用途 |
|-------|-----|------|------|
| `--text-h1` | `24px` | `32px` | 页面标题 |
| `--text-h2` | `20px` | `28px` | 区块标题 |
| `--text-h3` | `16px` | `24px` | 卡片标题 |
| `--text-body` | `14px` | `22px` | 正文 |
| `--text-body-lg` | `15px` | `24px` | 大号正文 |
| `--text-small` | `12px` | `18px` | 辅助文字、标签 |
| `--text-xs` | `11px` | `16px` | 极小文字（Badge 数字） |

### 3.3 字重

| Token | 值 | 用途 |
|-------|-----|------|
| `--weight-normal` | `400` | 正文 |
| `--weight-medium` | `500` | 按钮、Tab |
| `--weight-semibold` | `600` | 标题 |
| `--weight-bold` | `700` | 大标题 |

---

## 4. 圆角

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | `4px` | 小元素（Badge、Tag） |
| `--radius-md` | `8px` | 输入框、按钮、卡片 |
| `--radius-lg` | `12px` | 大卡片、Modal |
| `--radius-xl` | `16px` | 超大面板 |
| `--radius-full` | `9999px` | 圆形 / Pill 形状 |

---

## 5. 阴影

| Token | 值 | 用途 |
|-------|-----|------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | 卡片默认 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.35)` | 悬停卡片、Dropdown |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.4)` | Modal、弹窗 |
| `--shadow-xl` | `0 12px 36px rgba(0,0,0,0.5)` | Toast、Tooltip |

---

## 6. 过渡动画

| Token | 值 | 用途 |
|-------|-----|------|
| `--transition-fast` | `150ms ease` | 悬停、按下 |
| `--transition-normal` | `250ms ease` | 展开/收起 |
| `--transition-slow` | `350ms ease` | 页面切换 |

---

## 7. z-index 层级

| Token | 值 | 用途 |
|-------|-----|------|
| `--z-dropdown` | `100` | Dropdown / Select 弹出 |
| `--z-sticky` | `200` | 粘性头部 |
| `--z-modal-backdrop` | `300` | Modal 遮罩 |
| `--z-modal` | `400` | Modal 内容 |
| `--z-toast` | `500` | Toast 通知 |
| `--z-tooltip` | `600` | Tooltip |

---

## 8. 布局尺寸

| Token | 值 | 用途 |
|-------|-----|------|
| `--sidebar-width` | `240px` | 侧边栏宽度 |
| `--sidebar-collapsed` | `64px` | 折叠侧边栏宽度 |
| `--topbar-height` | `56px` | 顶部栏高度 |
| `--content-max-width` | `1280px` | 内容区最大宽度 |
| `--node-panel-width` | `280px` | 流程编辑器左侧节点面板宽度 |
| `--property-panel-width` | `320px` | 流程编辑器右侧属性面板宽度 |
