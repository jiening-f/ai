# ============================================
# ai-game-tool 构建打包脚本 (Windows)
# ============================================
# 用法: .\deploy\build.ps1
# 输出: dist/ 目录下生成 exe + 前端静态文件

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DistDir = Join-Path $ProjectRoot "dist"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ai-game-tool 构建打包" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --------------------------------------------------
# Step 1: 检查 Python 环境
# --------------------------------------------------
Write-Host "[1/4] 检查 Python 环境..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "X 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $($python.Source)" -ForegroundColor Green

# --------------------------------------------------
# Step 2: 安装后端依赖
# --------------------------------------------------
Write-Host "[2/4] 安装 Python 依赖..." -ForegroundColor Yellow
$reqFile = Join-Path $ProjectRoot "backend" "requirements.txt"
if (-not (Test-Path $reqFile)) {
    Write-Host "X 未找到 requirements.txt" -ForegroundColor Red
    exit 1
}

Push-Location $ProjectRoot
try {
    python -m pip install --upgrade pip -q
    pip install -r $reqFile -q
    Write-Host "  V 依赖安装完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# --------------------------------------------------
# Step 3: 复制前端静态文件
# --------------------------------------------------
Write-Host "[3/4] 准备前端静态文件..." -ForegroundColor Yellow
$frontendDist = Join-Path $ProjectRoot "frontend"
$staticDest = Join-Path $ProjectRoot "backend" "static"
if (Test-Path $staticDest) {
    Remove-Item -Recurse -Force $staticDest -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $staticDest -Force | Out-Null

# 复制前端 HTML/JS/CSS 到 static 目录作为内嵌资源
Copy-Item -Path "$frontendDist/*" -Destination $staticDest -Recurse -Force
Write-Host "  V 前端文件已复制到 static/" -ForegroundColor Green

# --------------------------------------------------
# Step 4: PyInstaller 打包
# --------------------------------------------------
Write-Host "[4/4] PyInstaller 打包..." -ForegroundColor Yellow

# 清理旧构建
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir -ErrorAction SilentlyContinue
}

$serverPy = Join-Path $ProjectRoot "backend" "server.py"
$specName = "game-tool"

Push-Location $ProjectRoot
try {
    pyinstaller `
        --name $specName `
        --onefile `
        --add-data "backend/static;static" `
        --add-data "backend/routes;routes" `
        --add-data "backend/engine;engine" `
        --add-data "backend/core;core" `
        --distpath $DistDir `
        --workpath build_temp `
        --specpath . `
        --hidden-import uvicorn `
        --hidden-import uvicorn.loggers `
        --hidden-import uvicorn.loops `
        --hidden-import uvicorn.loops.auto `
        --hidden-import uvicorn.protocols `
        --hidden-import uvicorn.protocols.http `
        --hidden-import uvicorn.protocols.http.auto `
        --hidden-import uvicorn.middleware `
        --hidden-import uvicorn.middleware.proxy_headers `
        --hidden-import fastapi `
        --hidden-import pydantic `
        --hidden-import pyautogui `
        --hidden-import numpy `
        --hidden-import cv2 `
        --hidden-import PIL `
        --hidden-import PIL.Image `
        --hidden-import PIL.ImageDraw `
        --collect-all pyautogui `
        --exclude-module torch `
        --exclude-module torchvision `
        --exclude-module easyocr `
        --exclude-module tensorflow `
        --exclude-module pandas `
        --exclude-module scipy `
        --exclude-module sklearn `
        --exclude-module matplotlib `
        --exclude-module skimage `
        $serverPy

    $exePath = Join-Path $DistDir "$specName.exe"
    if (Test-Path $exePath) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  V 构建成功!" -ForegroundColor Green
        Write-Host "  输出: $exePath" -ForegroundColor Green
        Write-Host "  大小: $((Get-Item $exePath).Length / 1MB -as [int]) MB" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
    } else {
        Write-Host "X 打包失败，未生成 exe 文件" -ForegroundColor Red
        Write-Host "  检查 build_temp 目录中的 warn-*.txt 文件了解详情" -ForegroundColor Yellow
        exit 1
    }
} finally {
    Pop-Location

    # 清理临时构建文件
    $buildDir = Join-Path $ProjectRoot "build_temp"
    if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue }
    $specFile = Join-Path $ProjectRoot "$specName.spec"
    if (Test-Path $specFile) { Remove-Item -Force $specFile -ErrorAction SilentlyContinue }
    $staticDir = Join-Path $ProjectRoot "backend" "static"
    if (Test-Path $staticDir) { Remove-Item -Recurse -Force $staticDir -ErrorAction SilentlyContinue }
}
