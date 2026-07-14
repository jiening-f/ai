## AIX-94 引擎进程分离 — 完成报告

### 新增文件

1. **`backend/engine/engine_process.py`** — 独立引擎子进程入口
   - CLI 参数：`--api-url`, `--execution-id`, `--mode` (script/node), `--config` (JSON)
   - 通过 `websockets` 库连接 API 的 `/api/ws/engine/{execution_id}` 端点
   - 使用 asyncio + 线程池执行器运行同步的 ScriptEngine / NodeEngine
   - 回调封装：`on_log` / `on_done` 自动转为 WS 消息
   - 支持控制指令：stop / pause / resume
   - 每 15 秒发送心跳
   - 连接失败自动重试（指数退避，最多 5 次）

2. **`backend/engine/process_manager.py`** — 进程生命周期管理器（单例）
   - `start_engine()` — 通过 `subprocess.Popen` 启动独立子进程
   - `stop_engine()` — 优雅终止（SIGTERM），超时后强制杀死
   - `get_engine_status()` / `list_engines()` — 状态查询
   - `update_heartbeat()` / `update_status()` — 供 WS handler 调用
   - `shutdown_all()` — 关闭时清理所有引擎
   - 后台线程每 10 秒检查心跳，30 秒超时自动判定死亡
   - 崩溃后最多重试 3 次，保留原配置重启动

### 修改文件

3. **`backend/app/api/websocket.py`** — 新增引擎 WebSocket 端点
   - 新增 `/api/ws/engine/{execution_id}` 端点，供引擎子进程连接
   - 引擎消息自动广播到 `/api/ws/execution/{execution_id}` 的前端客户端
   - 前端控制指令（stop / pause / resume）自动转发给引擎子进程
   - 引擎状态变更自动同步到数据库（`status`, `started_at`, `finished_at`, `duration_ms`）
   - 引擎断开连接时通知前端

4. **`backend/routes/run.py`** — 改为通过 ProcessManager 启动
   - 移除全局 ScriptEngine 实例
   - `POST /run` → `process_manager.start_engine(mode="script")`
   - `POST /stop` → `process_manager.stop_engine()`
   - `GET /status` → `process_manager.get_engine_status()`

5. **`backend/routes/nodes.py`** — 改为通过 ProcessManager 启动
   - 移除全局 NodeEngine 实例和线程管理
   - `POST /nodes/run` → `process_manager.start_engine(mode="node")`
   - `POST /nodes/stop` → `process_manager.stop_engine()`

6. **`backend/server.py`** — 引擎生命周期集成
   - lifespan 中初始化 / 清理引擎进程
   - 新增 `GET /api/engines` 端点查看所有活跃引擎
   - 健康检查 `/api/health` 返回引擎计数

### 架构示意

```
┌─────────────────────────────────────────────────┐
│  API 进程 (uvicorn)                              │
│                                                   │
│  ProcessManager (进程生命周期)                     │
│       │ spawn / kill                              │
│       ▼                                           │
│  ┌──────────┐    WS /api/ws/engine/{id}          │
│  │ 子进程 A │◄────────────────────────────────┐  │
│  │ (script) │   桥接到                          │  │
│  └──────────┘                                   │  │
│  ┌──────────┐    WS /api/ws/execution/{id}      │  │
│  │ 子进程 B │◄──────────────────────────────┐  │  │
│  │ (node)   │   前端 client                 │  │  │
│  └──────────┘                               │  │  │
│                                              ▼  ▼  ▼
│                                           前端浏览器
└─────────────────────────────────────────────────┘
```

### 验证结果

```
from backend.engine import engine_process     → OK
from backend.engine import process_manager    → OK
from backend.server import app                → OK
```

### 注意事项

- 引擎子进程通过 WS 连接回 API，API 服务器需先启动
- ScriptEngine 的 `_verify_game_window()` 在无游戏窗口句柄时跳过检测
- `pause/resume` 指令目前仅定义接口，引擎实际行为取决于后续实现
- 心跳超时 30 秒，崩溃最多重试 3 次
- 引擎状态同步使用数据库 `executions` 表的 status / started_at / finished_at / duration_ms / error_message 字段
