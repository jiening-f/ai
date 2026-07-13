# 图标占位

请将正式的 Tauri 应用图标放置在此目录。

Tauri v2 构建时需要的图标格式：

| 文件名 | 尺寸 | 平台 |
|--------|------|------|
| `32x32.png` | 32x32 | Windows |
| `128x128.png` | 128x128 | 通用 |
| `128x128@2x.png` | 256x256 | macOS Retina |
| `icon.icns` | 多尺寸 | macOS |
| `icon.ico` | 多尺寸 | Windows |
| `icon.png` | 自定义 | 系统托盘（建议 32x32） |

生成方法（需要安装 `@tauri-apps/cli`）：

```bash
npx tauri icon path/to/your-icon.png
```

这将自动生成所有需要的尺寸和格式。
