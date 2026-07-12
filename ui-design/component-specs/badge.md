# Badge 标签

## 用途
表示状态、分类、计数或属性标识。

## 视觉样式

### 尺寸

| 变体 | 高度 | 内边距 | 字号 |
|------|------|--------|------|
| sm | 20px | 4px 8px | 11px |
| md（默认） | 24px | 4px 10px | 12px |

### 颜色变体

| 变体 | 背景 | 文字色 |
|------|------|--------|
| **default** | `--border-default` | `--text-secondary` |
| **primary** | `--color-primary-bg` | `--color-primary` |
| **success** | `--color-success-bg` | `--color-success` |
| **warning** | `--color-warning-bg` | `--color-warning` |
| **error** | `--color-error-bg` | `--color-error` |

### 圆角

- 默认 `--radius-sm`（4px）
- Pill 变体 `--radius-full`（胶囊形）

### 带点 Badge（状态指示）

```
● 运行中    → 绿色圆点 + 文字
● 已暂停    → 黄色圆点 + 文字
● 已停止    → 灰色圆点 + 文字
```

圆点 8px，与文字间距 6px。

### 数字 Badge

- 用于图标右上角显示未读数
- 位置绝对定位，`--radius-full`，最小宽度等于高度
- 数字超过 99 显示 "99+"
