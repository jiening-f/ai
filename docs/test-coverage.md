# 测试覆盖报告

> 生成日期: 2026-07-13 | pytest 版本: 9.1.1 | 测试框架: pytest + vitest

---

## 概述

| 指标 | 数值 |
|------|------|
| 总测试数 | 174 (pytest) + 12 (vitest) |
| 测试文件数 | 8 |
| 通过率 | 100% |

---

## 后端引擎层测试覆盖

### 1. 节点类型测试 (`tests/engine/test_nodes.py`) — 52 个测试

覆盖所有 6 种 BaseNode 子类 + 2 种枚举/数据类：

| 节点类型 | 测试项 | 覆盖内容 |
|----------|--------|---------|
| `NodeStatus` | 3 | 枚举值、等值比较、语义验证 |
| `NodeResult` | 4 | 创建成功/失败结果、默认值、next_node |
| `BaseNode` | 9 | 属性、配置、validate()、get_next_node()、to_dict()、repr() |
| `StartNode` | 4 | node_type、validate()、execute() 返回 SUCCESS、日志输出 |
| `EndNode` | 4 | node_type、validate()、execute() 返回 None next_node、日志 |
| `WaitNode` | 8 | node_type、正/零/负/缺失/非数值 duration 验证、execute 异步等待 |
| `LogNode` | 3 | node_type、带消息 execute、默认消息 execute |
| `ConditionNode` | 8 | True/False 求值、异常表达式、true/false 分支、next_nodes fallback、变量条件 |
| `LoopNode` | 7 | 循环/退出、计数器递增、max_iterations、条件驱动、异常表达式 |

### 2. 执行器状态机测试 (`tests/engine/test_executor.py`) — 28 个测试

| 测试类 | 测试数 | 覆盖状态转换 |
|--------|--------|-------------|
| `TestEngineState` | 2 | 6 种状态枚举 |
| `TestStateMachine` | 6 | idle→running→completed、线性流程、缺失节点→error、重新运行 |
| `TestPauseResume` | 2 | running→paused、paused→running |
| `TestStop` | 2 | running→stopped、idle→stopped |
| `TestStepMode` | 1 | idle 单步启动 |
| `TestErrorHandling` | 3 | stop/continue/retry 策略 |
| `TestConditionBranch` | 2 | 真/假分支 |
| `TestLoopFlow` | 1 | 循环计数 |
| `TestCallbacks` | 2 | 状态回调、节点回调 |
| `TestCreateRunner` | 4 | 工厂函数、日志/性能/反检测选项 |

**状态机覆盖**:
- ✅ idle → running
- ✅ running → completed
- ✅ running → paused → running
- ✅ running → stopped
- ✅ idle → stopped
- ✅ running → error (start 节点缺失)
- ✅ running → error (节点执行异常 + on_error=stop)

### 3. 执行上下文测试 (`tests/engine/test_context.py`) — 24 个测试

| 测试类 | 覆盖方法/属性 |
|--------|-------------|
| `TestVariables` | get_var(), set_var(), get_all_variables(), get_node_output(), set_node_output() |
| `TestScreenshots` | cache_screenshot(), get_screenshot(), clear_screenshots() |
| `TestLogging` | info(), warn(), error(), log(), get_logs(), get_recent_logs(), timestamp |
| `TestStats` | mark_start(), mark_executed(), mark_current_node(), stats, elapsed_ms |
| `TestStateControl` | pause(), resume(), stop(), is_active(), enable_step_mode(), step_once() |
| `TestIntegration` | 完整生命周期模拟 |

### 4. 钩子系统测试 (`tests/engine/test_hooks.py`) — 18 个测试

| 测试类 | 覆盖内容 |
|--------|---------|
| `TestHookSystem` | 注册/移除/清空 pre/post 钩子、拦截执行、异常安全、多钩子顺序 |
| `TestLoggingHooks` | create_logging_hooks()、pre 日志、post 成功/失败日志 |
| `TestPerformanceHooks` | 计时对、pre→post 周期、无 pre 时的安全处理 |
| `TestAntiDetectHook` | 延迟范围、默认参数 |

### 5. 视觉识别模块测试 (`tests/engine/test_vision.py`) — 17 个测试

| 测试类 | 覆盖内容 |
|--------|---------|
| `TestOCRInstance` | 单例、初始状态、引擎切换、已加载跳过 |
| `TestOCRPreprocess` | 游戏字体预处理（放大、灰度、OTSU二值化） |
| `TestTemplateMatcherPreprocess` | CLAHE 灰度、Canny 边缘检测 |
| `TestTemplateColorSimilarity` | 相同图像、不同图像、极小图像的颜色相似度 |
| `TestTemplateMatcherFind` | 不存在文件、无名称模板 |
| `TestScreenshotCapture` | 接口存在性验证 |
| `TestFastMode` | 快速模式开关 |
| `TestLegacyAliases` | 旧接口别名 tmpl_find, ocr_find, _shot |

### 6. 后端 NodeEngine 测试 (`tests/backend/test_node_engine.py`) — 15 个测试

在隔离子进程中运行，覆盖：

| 测试项 | 覆盖内容 |
|--------|---------|
| 枚举 | NodeType(3)、DetectType(3)、Decision(2) |
| FeatureNode | 创建(text/image/key)、禁用、默认值 |
| MapConfig | 创建、禁用地图、空特征 |
| NodeFlow | 创建、默认值、max_loops |
| NodeEngine | 初始化、空流程、detect 键/文本/图片、全部通过、重开、禁用特征、max_loops 限制 |

---

## 前端测试覆盖

### 7. React 组件测试 (`frontend/src/__tests__/components.test.tsx`) — 12 个测试

| 组件 | 测试数 | 覆盖内容 |
|------|--------|---------|
| Modal | 7 | 显隐切换、标题/内容/关闭/遮罩/点击内部/footer/size class |
| ConfirmDialog | 6 | 消息渲染、默认/自定义按钮、确认/取消回调、danger/primary 图标 |
| ToastProvider | 2 | 子组件渲染、Provider 外抛错 |

### 8. 前端节点定义测试 (`tests/frontend/test_node_definitions.py`) — 17 个测试

验证 17 种 UI 节点类型：
- 5 个分类完整性
- 17 种节点无重复类型
- 每个节点的 type/label/icon 字段
- 特定节点验证（start、end、键盘/鼠标/视觉/数据操作）
- CanvasNode 数据结构
- 默认画布节点 y 坐标递增

---

## 未被覆盖的领域（已知限制）

| 模块 | 原因 |
|------|------|
| OCR 实际识别（Windows OCR / EasyOCR） | 需要 Windows 桌面环境和 OCR 引擎 |
| 截图 GDI/PrintWindow | 需要 Windows 桌面环境和游戏窗口 |
| 模板匹配实际 find()（完整流程） | 需要 OpenCV + 模板文件 |
| 输入模拟（pyautogui） | 需要桌面环境 |
| FastAPI 路由集成测试 | 需要启动服务器 |
| 数据库 models.py | 需要 SQLite 连接 |

---

## 运行测试

```bash
# 后端测试
cd ai && python -m pytest tests/ -v

# 前端测试（需先 npm install）
cd ai/frontend && npm test
```
