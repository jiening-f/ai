# game-tool — 架构计划

> 版本: 1.0 | 日期: 2026-07-12 | 作者: Claude-1

---

## 一、项目定位

一款现代化、模块化、跨平台的游戏自动化脚本工具。支持可视化流程编排、多种视觉识别引擎、灵活的输入模拟方式，通过 Web 控制台进行管理。

**核心原则：**
- 模块低耦合，各模块可独立开发、测试、替换
- 插件式架构，游戏配置作为独立包热加载
- 异步优先，事件驱动
- 先跑通核心链路，再逐步完善

---

## 二、技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | Python FastAPI | 异步原生支持，生态成熟，与 OpenCV/pyautogui 无缝集成 |
| 前端框架 | React 18 + TypeScript + Vite | 生态最大，ReactFlow 流程编辑器成熟 |
| 流程编辑器 | @xyflow/react (ReactFlow) | 拖拽式节点编排，支持自定义节点 |
| 桌面封装 | 待定（先跑通 Web，再评估 Electron/Tauri） |
| 数据库 | SQLite + SQLAlchemy (async) | 本地轻量，无需额外安装 |
| 视觉识别 | OpenCV + PaddleOCR/EasyOCR 双引擎 | OpenCV 模板匹配成熟，PaddleOCR 中文最优 |
| 输入模拟 | pyautogui + pydirectinput + win32api | 覆盖前台/后台输入 |
| 实时通信 | WebSocket (FastAPI built-in) | 低延迟双向推送 |
| 测试 | pytest + pytest-asyncio | FastAPI 官方推荐 |

---

## 三、目录结构

```
apps/game-tool/
├── backend/                    # Python FastAPI 后端 [后端工程师]
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 配置管理（环境变量/配置文件）
│   │   ├── api/                # REST API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── game.py         # 游戏管理 API
│   │   │   ├── preset.py       # 预设管理 API
│   │   │   ├── script.py       # 脚本执行 API
│   │   │   ├── screenshot.py   # 截图 API
│   │   │   ├── plugin.py       # 插件管理 API
│   │   │   ├── settings.py     # 系统设置 API
│   │   │   └── websocket.py    # WebSocket 端点
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── game.py
│   │   │   ├── preset.py
│   │   │   ├── execution.py
│   │   │   ├── plugin.py
│   │   │   └── settings.py
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── game.py
│   │   │   ├── preset.py
│   │   │   └── ...
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── game_service.py
│   │   │   ├── preset_service.py
│   │   │   └── ...
│   │   └── database.py         # 数据库连接与会话管理
│   ├── requirements.txt
│   └── server.py               # 启动脚本
│
├── engine/                     # 核心引擎 [Claude-1]
│   ├── __init__.py
│   ├── executor/               # 脚本执行器
│   │   ├── __init__.py
│   │   ├── engine.py           # 主执行引擎（事件驱动）
│   │   ├── context.py          # 执行上下文
│   │   └── scheduler.py        # 节点调度器
│   ├── nodes/                  # 节点定义（19种）
│   │   ├── __init__.py
│   │   ├── base.py             # 节点基类
│   │   ├── flow.py             # 流程控制节点（开始/结束/等待/条件/循环）
│   │   ├── keyboard.py         # 键盘节点
│   │   ├── mouse.py            # 鼠标节点
│   │   ├── vision.py           # 视觉识别节点（OCR/模板匹配/截图）
│   │   ├── data.py             # 数据操作节点（变量/文本输出）
│   │   └── registry.py         # 节点注册表
│   ├── vision/                 # 视觉识别模块
│   │   ├── __init__.py
│   │   ├── ocr.py              # OCR 引擎（PaddleOCR/EasyOCR）
│   │   ├── template.py         # 模板匹配（OpenCV）
│   │   └── screenshot.py       # 截图工具
│   ├── input/                  # 输入模拟模块
│   │   ├── __init__.py
│   │   ├── keyboard.py         # 键盘模拟
│   │   ├── mouse.py            # 鼠标模拟
│   │   └── recorder.py         # 输入录制与回放
│   ├── window/                 # 窗口管理模块
│   │   ├── __init__.py
│   │   └── manager.py          # 窗口枚举/绑定/操作
│   └── plugin/                 # 插件系统
│       ├── __init__.py
│       ├── loader.py           # 插件加载器
│       └── hooks.py            # Hook 定义
│
├── frontend/                   # React 前端 [前端工程师]
│   ├── src/
│   │   ├── main.tsx            # 入口
│   │   ├── App.tsx             # 路由配置
│   │   ├── api/                # API 请求封装
│   │   ├── pages/              # 页面（7个核心页面）
│   │   │   ├── Dashboard.tsx
│   │   │   ├── GameManager.tsx
│   │   │   ├── PresetEditor.tsx
│   │   │   ├── FlowEditor.tsx  # 可视化流程编辑器
│   │   │   ├── ExecutionHistory.tsx
│   │   │   ├── PluginManager.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/         # 通用组件
│   │   │   ├── layout/        # 布局组件
│   │   │   ├── nodes/         # 流程编辑器节点组件
│   │   │   └── common/        # 通用 UI 组件
│   │   ├── hooks/              # 自定义 Hooks
│   │   │   ├── useWebSocket.ts
│   │   │   └── useApi.ts
│   │   ├── stores/             # 状态管理 (Zustand)
│   │   └── styles/             # 样式文件
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── database/                   # 数据库 [数据库管理]
│   ├── schema.sql              # 完整建表语句
│   ├── migrations/             # 迁移脚本
│   └── seeds/                  # 种子数据（游戏预设模板）
│
├── ui-design/                  # UI 设计规范 [UI-Designer]
│   ├── design-tokens.md        # 设计 Token（颜色/间距/字体）
│   ├── component-specs/        # 组件规格说明
│   └── page-mockups/           # 页面布局描述
│
├── deploy/                     # 部署配置 [运维部署]
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── build.ps1               # Windows 打包脚本
│   └── nginx.conf
│
├── tests/                      # 测试
│   ├── test_engine/
│   ├── test_backend/
│   └── conftest.py
│
└── docs/                       # 文档
    ├── architecture.md         # 本文档
    ├── progress.md             # 进度日志
    └── api-spec.md             # API 规范（待生成）
```

---

## 四、核心模块设计

### 4.1 脚本引擎 (engine/)

**事件驱动架构：**
```
用户触发 → API → ExecutionEngine.start()
                          ↓
              Scheduler（节点调度器）
                  ↓       ↓       ↓
              Node A → Node B → Node C
                  ↓
         ExecutionContext（共享上下文：变量、截图缓存、运行状态）
                  ↓
         WebSocket 实时推送（当前节点、中间数据、日志）
```

**节点基类设计：**
```python
class BaseNode:
    node_id: str
    node_type: str       # 19种类型之一
    config: dict          # 节点配置参数
    next_nodes: list[str] # 后继节点 ID 列表
    condition: str | None # 条件表达式（条件节点专用）

    async def execute(self, ctx: ExecutionContext) -> NodeResult
    def validate(self) -> bool
```

**19 种节点类型：**
| 分类 | 节点类型 | 说明 |
|------|---------|------|
| 流程控制 | start, end, wait, condition, loop | 开始、结束、等待、条件分支、循环 |
| 键盘 | key_press, key_combo, key_hold | 单键、组合键、长按 |
| 鼠标 | mouse_click, mouse_dblclick, mouse_right, mouse_drag, mouse_scroll | 点击、双击、右键、拖拽、滚动 |
| 视觉 | ocr_recognize, template_match, screenshot | OCR识别、模板匹配、截图 |
| 数据 | variable_set, text_output | 变量赋值、文本输出 |

**执行状态机：**
```
IDLE → RUNNING → PAUSED → RUNNING → COMPLETED
                 ↘ STOPPED
```

### 4.2 视觉识别 (engine/vision/)

**双引擎策略：**
1. PaddleOCR（首选）— 中文识别最优，离线可用
2. EasyOCR（降级）— 安装更简单，作为 fallback

**模板匹配流程：**
```
截图 → 灰度化 → 多尺度模板匹配 → NMS去重 → 返回坐标+置信度
```

### 4.3 输入模拟 (engine/input/)

**分层设计：**
1. **高层 API** — pyautogui（简单可靠）
2. **中层 API** — pydirectinput（游戏兼容性更好）
3. **底层 API** — win32api SendMessage/PostMessage（支持后台模式）

### 4.4 窗口管理 (engine/window/)

使用 Win32 API 实现：
- 按标题/类名枚举窗口
- 获取窗口位置、大小、句柄
- 前置、移动、调整窗口
- 绑定脚本执行目标窗口

### 4.5 可视化流程编辑器 (frontend/)

基于 ReactFlow (@xyflow/react)：
- 拖拽节点从侧边栏到画布
- 节点间连线表示执行顺序
- 条件节点支持多输出端口（true/false）
- 循环节点支持子流程
- 执行时高亮当前节点，显示中间数据

### 4.6 插件系统 (engine/plugin/)

**Hook 生命周期：**
```
on_script_start → on_node_before → on_node_after → ... → on_script_end
```

---

## 五、数据库设计

### 5.1 核心表（6张）

```sql
-- 游戏配置
games (id, name, window_title, window_class, created_at, updated_at)

-- 预设配置（每个游戏可有多套预设）
presets (id, game_id FK, name, description, flow_data JSON, created_at, updated_at)

-- 执行记录
executions (id, preset_id FK, status, started_at, finished_at, duration_ms, error_message)

-- 执行步骤日志
execution_steps (id, execution_id FK, node_id, node_type, status, input_data, output_data, started_at, finished_at)

-- 插件
plugins (id, name, version, author, enabled, installed_at)

-- 系统设置
settings (key UNIQUE, value, updated_at)
```

---

## 六、API 设计

### 6.1 REST API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/games | 游戏列表 |
| POST | /api/games | 添加游戏 |
| GET | /api/games/{id}/presets | 游戏的预设列表 |
| POST | /api/presets/{id}/run | 执行预设 |
| POST | /api/presets/{id}/stop | 停止执行 |
| POST | /api/presets/{id}/pause | 暂停执行 |
| POST | /api/presets/{id}/resume | 恢复执行 |
| POST | /api/presets/{id}/step | 单步执行 |
| GET | /api/screenshot | 获取当前截图 |
| GET | /api/executions | 执行历史 |
| WS | /ws | 实时通信 |

---

## 七、阶段规划

### Phase 1 — 基础骨架 (本期)
**目标：** 项目能跑起来，前后端联通

| 任务 | 负责人 | 产出 |
|------|--------|------|
| 后端项目骨架 | 后端工程师 | FastAPI 入口 + 配置 + 数据库连接 + 基础路由 |
| 前端项目骨架 | 前端工程师 | Vite + React + 路由 + 基础布局 |
| 引擎节点定义 | Claude-1 | 19 种节点类定义 + 注册表 + 基类 |
| 数据库 Schema | 数据库管理 | 6 张表建表 SQL + SQLAlchemy 模型 |
| UI 设计规范 | UI-Designer | 设计 Token + 7 个页面布局描述 |
| 部署配置 | 运维部署 | Dockerfile + docker-compose + 构建脚本 |

### Phase 2 — 核心引擎
**目标：** 脚本能执行，视觉识别能工作

### Phase 3 — Web 控制台
**目标：** 可视化流程编辑器可用

### Phase 4 — 集成与发布
**目标：** 打包成可分发应用

---

## 八、通信协议

### WebSocket 消息格式

```json
{
  "type": "execution_update | log | screenshot | error",
  "data": { ... },
  "timestamp": "2026-07-12T08:00:00Z"
}
```

### 消息类型
- `execution_update` — 执行状态变化、当前节点
- `log` — 执行日志
- `screenshot` — 截图 base64
- `error` — 错误信息

---

## 九、非功能需求

- **性能：** 脚本执行延迟 < 50ms，WebSocket 推送延迟 < 100ms
- **可靠性：** 脚本异常时自动保存现场，支持恢复
- **可扩展：** 新增节点类型只需注册即可，不改核心代码
- **安全：** 插件在沙箱中运行，敏感信息用环境变量
