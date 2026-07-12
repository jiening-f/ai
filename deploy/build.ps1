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
    Write-Host "✗ 未找到 Python，请先安装 Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $($python.Source)" -ForegroundColor Green

# --------------------------------------------------
# Step 2: 安装后端依赖
# --------------------------------------------------
Write-Host "[2/4] 安装 Python 依赖..." -ForegroundColor Yellow
$reqFile = Join-Path $ProjectRoot "backend" "requirements.txt"
if (-not (Test-Path $reqFile)) {
    Write-Host "✗ 未找到 requirements.txt" -ForegroundColor Red
    exit 1
}

Push-Location $ProjectRoot
try {
    python -m pip install --upgrade pip -q
    pip install -r $reqFile -q
    Write-Host "  ✓ 依赖安装完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# --------------------------------------------------
# Step 3: 构建前端
# --------------------------------------------------
Write-Host "[3/4] 构建前端..." -ForegroundColor Yellow
$frontendDir = Join-Path $ProjectRoot "frontend"
if (Test-Path (Join-Path $frontendDir "package.json")) {
    Push-Location $frontendDir
    try {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            Write-Host "✗ 未找到 npm，跳过前端构建" -ForegroundColor Red
        } else {
            npm install --silent
            npm run build
            Write-Host "  ✓ 前端构建完成" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  - 未找到 frontend/package.json，跳过前端构建" -ForegroundColor Gray
}

# --------------------------------------------------
# Step 4: PyInstaller 打包
# --------------------------------------------------
Write-Host "[4/4] PyInstaller 打包..." -ForegroundColor Yellow

# 清理旧构建
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}

$serverPy = Join-Path $ProjectRoot "backend" "server.py"
$specName = "ai-game-tool"

Push-Location $ProjectRoot
try {
    pyinstaller `
        --name $specName `
        --onefile `
        --add-data "frontend/dist;frontend/dist" `
        --add-data "backend/app;backend/app" `
        --distpath $DistDir `
        --workpath build `
        --specpath . `
        --hidden-import uvicorn `
        --hidden-import sqlalchemy.ext.asyncio `
        --hidden-import aiosqlite `
        --collect-all sqlalchemy `
        $serverPy

    if (Test-Path (Join-Path $DistDir "$specName.exe")) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  ✓ 构建成功!" -ForegroundColor Green
        Write-Host "  输出: $DistDir\$specName.exe" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
    } else {
        Write-Host "✗ 打包失败，未生成 exe 文件" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location

    # 清理临时构建文件
    $buildDir = Join-Path $ProjectRoot "build"
    if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue }
    $specFile = Join-Path $ProjectRoot "$specName.spec"
    if (Test-Path $specFile) { Remove-Item -Force $specFile -ErrorAction SilentlyContinue }
}
