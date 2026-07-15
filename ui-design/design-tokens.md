# Design Token 体系 — 游戏全能脚本

> 版本：v1.0 | 基准：4px 原子化网格 | 暗色优先，亮色互补

---

## 1. 颜色 (Color)

### 1.1 主题色板

| Token | 暗色 Theme | 亮色 Theme | 用途 |
|-------|-----------|-----------|------|
| `--color-bg` | `#0f0f11` | `#f5f5f7` | 页面背景 |
| `--color-surface` | `#1a1a1e` | `#ffffff` | 卡片/面板表面 |
| `--color-surface-hover` | `#242428` | `#f0f0f2` | 表面悬停态 |
| `--color-surface-raised` | `#222226` | `#fafafa` | 弹窗/下拉表面 |
| `--color-border` | `#2e2e32` | `#e4e4e7` | 边框/分割线 |
| `--color-border-hover` | `#3e3e42` | `#d4d4d8` | 边框悬停态 |

### 1.2 品牌色

| Token | 色值 | 用途 |
|-------|------|------|
| `--color-primary` | `#6366f1` | 主按钮/激活态/链接 |
| `--color-primary-hover` | `#818cf8` | 主按钮悬停 |
| `--color-primary-soft` | `rgba(99, 102, 241, 0.12)` | 主色背景/选中态 |
| `--color-primary-soft-hover` | `rgba(99, 102, 241, 0.2)` | 主色背景悬停 |

### 1.3 语义色

| Token | 暗色 | 亮色 | 用途 |
|-------|------|------|------|
| `--color-success` | `#22c55e` | `#16a34a` | 成功/运行中 |
| `--color-warning` | `#f59e0b` | `#d97706` | 警告/待处理 |
| `--color-error` | `#ef4444` | `#dc2626` | 错误/停止 |
| `--color-info` | `#3b82f6` | `#2563eb` | 信息提示 |

### 1.4 文字色

| Token | 暗色 | 亮色 | 用途 |
|-------|------|------|------|
| `--color-text-primary` | `#f1f1f3` | `#18181b` | 主文字 |
| `--color-text-secondary` | `#a1a1aa` | `#52525b` | 辅助文字 |
| `--color-text-muted` | `#52525b` | `#a1a1aa` | 置灰文字 |
| `--color-text-inverse` | `#18181b` | `#f1f1f3` | 反色文字（按钮上） |

---

## 2. 间距 (Spacing)

基于 4px 原子化网格：

| Token | 值 | 场景 |
|-------|-----|------|
| `--space-1` | 4px | 微间距 |
| `--space-2` | 8px | 内边距紧凑 |
| `--space-3` | 12px | 内边距常规 |
| `--space-4` | 16px | 卡片内边距 |
| `--space-5` | 20px | 组件间距 |
| `--space-6` | 24px | 区块间距 |
| `--space-8` | 32px | 大区块间距 |
| `--space-10` | 40px | 段落间距 |
| `--space-12` | 48px | 页面边距 |
| `--space-16` | 64px | 超大间距 |

---

## 3. 圆角 (Border Radius)

| Token | 值 | 场景 |
|-------|-----|------|
| `--radius-sm` | 4px | 小元素/标签 |
| `--radius-md` | 8px | 输入框/普通按钮 |
| `--radius-lg` | 12px | 卡片/弹窗 |
| `--radius-xl` | 16px | 大弹窗/页面卡片 |
| `--radius-full` | 9999px | 头像/徽标 |

---

## 4. 阴影 (Shadow)

### 4.1 暗色阴影

| Token | 值 | 场景 |
|-------|-----|------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | 浅层悬浮 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | 卡片悬浮 |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.5)` | 弹窗 |
| `--shadow-xl` | `0 12px 48px rgba(0,0,0,0.6)` | 通知/顶层 |

### 4.2 亮色阴影

| Token | 值 |
|-------|-----|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.08)` |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.1)` |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.12)` |
| `--shadow-xl` | `0 12px 48px rgba(0,0,0,0.15)` |

---

## 5. 字体 (Typography)

| Token | 值 | 场景 |
|-------|-----|------|
| `--font-family` | `'Inter', system-ui, -apple-system, sans-serif` | 正文字体 |
| `--font-mono` | `'JetBrains Mono', 'Fira Code', monospace` | 等宽字体 |

| Token | 字号 | 行高 | 字重 | 场景 |
|-------|------|------|------|------|
| `--text-xs` | 12px | 16px | 400 | 辅助文字 |
| `--text-sm` | 14px | 20px | 400 | 正文副信息 |
| `--text-base` | 16px | 24px | 400 | 正文 |
| `--text-lg` | 18px | 28px | 500 | 小标题 |
| `--text-xl` | 20px | 28px | 600 | 卡片标题 |
| `--text-2xl` | 24px | 32px | 700 | 页面标题 |
| `--text-3xl` | 30px | 36px | 700 | 大标题 |

---

## 6. 动效 (Animation)

| Token | 值 | 场景 |
|-------|-----|------|
| `--duration-fast` | 150ms | 悬停/按下态 |
| `--duration-normal` | 200ms | 切换/显示隐藏 |
| `--duration-slow` | 300ms | 弹窗出现/消失 |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | 退场缓动 |
| `--ease-in` | `cubic-bezier(0.4, 0, 0.2, 1)` | 进场缓动 |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 弹性效果 |

---

## 7. 组件尺寸

| 组件 | 高度 | 圆角 | 内边距 |
|------|------|------|--------|
| 按钮 - sm | 32px | 6px | 12px 16px |
| 按钮 - md | 40px | 8px | 16px 24px |
| 按钮 - lg | 48px | 10px | 20px 32px |
| 输入框 | 40px | 8px | 12px 16px |
| 游戏卡片 | 160px | 12px | 20px |
| 弹窗 (Dialog) | auto | 16px | 24px |

---

## 8. CSS 变量使用示例

```css
/* 游戏卡片 */
.game-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.game-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
```
