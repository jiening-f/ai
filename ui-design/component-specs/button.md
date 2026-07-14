# Button 按钮

## 用途
用户触发操作的主要交互元素。

## 视觉样式

### 尺寸变体

| 变体 | 高度 | 内边距 | 字号 |
|------|------|--------|------|
| sm | 32px | 12px 16px | 12px |
| md（默认） | 36px | 8px 20px | 14px |
| lg | 44px | 12px 28px | 16px |

### 类型变体

| 类型 | 背景 | 文字色 | 边框 |
|------|------|--------|------|
| **Primary** | `--color-primary` | 白色 | 无 |
| **Secondary** | 透明 | `--text-primary` | `--border-default` |
| **Ghost** | 透明 | `--text-secondary` | 无 |
| **Danger** | `--color-error` | 白色 | 无 |

### 交互状态

| 状态 | Primary | Secondary | Ghost | Danger |
|------|---------|-----------|-------|--------|
| 默认 | `#4f46e5` | 透明边框 | 透明 | `#ef4444` |
| 悬停 | `#6366f1` | `--bg-card-hover` | `--bg-card-hover` | `#dc2626` |
| 按下 | `#4338ca` | `--bg-card` | `--bg-card` | `#b91c1c` |
| 禁用 | 不透明度 40% | 不透明度 40% | 不透明度 40% | 不透明度 40% |

### 圆角
始终使用 `--radius-md`（8px）。

### 其他

- **Loading 态**: 按钮文字前显示 14px 旋转圆圈动画
- **Icon 按钮**: 正方形，宽高等于高度，无文字
- **全宽按钮**: `width: 100%`

## 交互细则

- 点击时无外发光，改为按下时背景略微加深
- 禁用态 `cursor: not-allowed`，不响应点击
- Loading 态禁用点击
