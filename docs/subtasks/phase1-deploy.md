## 任务：部署配置

### 目标
准备项目的部署和打包基础设施配置。

### 工作目录
`deploy/`

### 要求

1. **Docker 配置**
   - `Dockerfile` — 多阶段构建
     - 阶段 1: 安装 Python 依赖
     - 阶段 2: 安装 Node 依赖 + 构建前端
     - 阶段 3: 运行镜像（Python + 构建后的前端静态文件）
   - `docker-compose.yml` — 本地开发环境一键启动
     - backend 服务（端口 8765）
     - frontend 开发服务（可选，也可本地跑）

2. **构建脚本**
   - `build.ps1` — Windows PowerShell 打包脚本
     - 检查 Python 环境
     - 安装依赖
     - 构建前端
     - 用 PyInstaller 打包后端为 exe
     - 输出到 dist/ 目录

3. **Nginx 配置**
   - `nginx.conf` — 生产环境反向代理
     - 前端静态文件
     - /api/* 代理到后端
     - /ws 代理到后端 WebSocket

4. **其他**
   - `.gitignore` 放在项目根目录
     ```
     __pycache__/
     *.pyc
     node_modules/
     dist/
     .env
     backend/data/
     *.spec
     build/
     ```
   - 不需要 `.env.example`，配置在 config.py 中硬编码默认值

5. **产出文件**
   ```
   deploy/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── build.ps1
   └── nginx.conf
   ```

### 参考架构
详见 `docs/architecture.md` 第三节目录结构。
