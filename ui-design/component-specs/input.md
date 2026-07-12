# Input 输入框

## 用途
单行文本输入。

## 视觉样式

| 属性 | 值 |
|------|-----|
| 高度 | 36px（md）/ 32px（sm）/ 44px（lg） |
| 内边距 | 8px 12px |
| 背景 | `--bg-input` |
| 文字色 | `--text-primary` |
| 占位符色 | `--text-tertiary` |
| 边框 | `--border-default`，1px solid |
| 圆角 | `--radius-md`（8px） |

### 交互状态

| 状态 | 样式 |
|------|------|
| 默认 | 灰色边框 |
| 悬停 | 边框变亮 `--border-hover` |
| 聚焦 | 边框 `--color-primary`，无外发光 |
| 禁用 | 不透明度 50%，`cursor: not-allowed` |
| 错误 | 边框 `--color-error` |

### 前缀/后缀

- **前缀图标**: 在输入框左侧，灰色 `--text-tertiary`
- **后缀图标/按钮**: 在输入框右侧（如密码切换可见、清空按钮）

## 其他变体

- **Search**: 左侧搜索图标，右侧可按 Esc 清空
- **Password**: 右侧眼睛图标切换明文/密文
