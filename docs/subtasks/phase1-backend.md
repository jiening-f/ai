## 任务：后端项目骨架搭建

### 目标
搭建 FastAPI 后端项目基础结构，确保项目能启动、基础路由可访问。

### 工作目录
`backend/`

### 要求

1. **项目结构**
   ```
   backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py          # FastAPI 应用入口，CORS 配置
   │   ├── config.py         # 配置管理（Settings 类，读环境变量）
   │   ├── database.py       # SQLAlchemy async 引擎 + session
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── health.py     # GET /api/health → {"status": "ok"}
   │   ├── models/
   │   │   ├── __init__.py
   │   │   └── base.py       # SQLAlchemy Base
   │   └── schemas/
   │       └── __init__.py
   ├── requirements.txt
   └── server.py             # uvicorn 启动脚本
   ```

2. **依赖 (requirements.txt)**
   - fastapi
   - uvicorn[standard]
   - sqlalchemy[asyncio]
   - aiosqlite
   - pydantic
   - pydantic-settings

3. **数据库**
   - 使用 SQLite + aiosqlite
   - 数据库文件放在 `backend/data/` 目录
   - 启动时自动创建表和目录

4. **配置**
   - 数据库路径可配置
   - CORS 允许 localhost:5173（前端开发服务器）
   - 端口 8765

5. **验证**
   - `cd backend && python server.py` 能启动
   - `GET http://localhost:8765/api/health` 返回 `{"status": "ok"}`
   - 启动后 backend/data/ 目录自动创建

### 参考架构
详见 `docs/architecture.md` 第三节目录结构和第六节 API 设计。
