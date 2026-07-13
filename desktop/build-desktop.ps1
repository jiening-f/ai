# 全能脚本 — Tauri 桌面端构建脚本
# 用法: .\build-desktop.ps1

$ErrorActionPreference = "Stop"

Write-Host "===== 1. 构建前端 =====" -ForegroundColor Cyan
Push-Location ../frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    throw "前端构建失败"
}
Pop-Location

Write-Host "===== 2. 复制后端打包产物 =====" -ForegroundColor Cyan
# 假设后端已经通过 PyInstaller 打包为 dist/backend.exe
if (Test-Path ../dist/backend.exe) {
    Copy-Item ../dist/backend.exe ./src-tauri/backend-x86_64-pc-windows-msvc.exe -Force
    Write-Host "后端打包产物已复制" -ForegroundColor Green
}
else {
    Write-Warning "未找到 ../dist/backend.exe，请先打包后端：pyinstaller backend/server.py --name backend"
}

Write-Host "===== 3. 构建 Tauri 桌面应用 =====" -ForegroundColor Cyan
npm run tauri build
if ($LASTEXITCODE -ne 0) {
    throw "Tauri 构建失败"
}

Write-Host "===== 构建完成 =====" -ForegroundColor Green
