# 插件 API 文档

> 版本：1.0 | 适用于全能脚本 v2.0+

插件系统允许第三方开发者扩展全能脚本的功能，包括注册自定义节点类型、注入生命周期钩子、以及添加新的配置项。

---

## 目录

1. [快速开始](#1-快速开始)
2. [插件生命周期](#2-插件生命周期)
3. [BasePlugin 基类](#3-baseplugin-基类)
4. [七种生命周期钩子](#4-七种生命周期钩子)
5. [自定义节点注册](#5-自定义节点注册)
6. [插件配置系统](#6-插件配置系统)
7. [PluginManager 管理器](#7-pluginmanager-管理器)
8. [端到端教程](#8-端到端教程)
9. [API 参考速查](#9-api-参考速查)

---

## 1. 快速开始

### 1.1 最简插件

创建一个 `my_plugin.py`：

```python
from engine.plugin.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    author = "你的名字"
    description = "我的第一个插件"
```

这已经是一个合法插件了 —— 虽然它什么都不做。接下来逐步添加功能。

### 1.2 目录约定

第三方插件可以放在任意位置，推荐的结构：

```
plugins/                          # 项目级插件目录
└── my_plugin/
    ├── __init__.py               # 导出插件类
    ├── plugin.py                 # 插件主类
    ├── nodes.py                  # 自定义节点（可选）
    └── settings.json             # 默认配置（可选）
```

### 1.3 加载插件

```python
from engine.plugin.base import PluginManager

manager = PluginManager()
manager.load(MyPlugin())

# 将插件的钩子系统注入执行器
from engine.executor.runner import ScriptRunner
runner = ScriptRunner(nodes, hooks=manager.hook_system)
```

---

## 2. 插件生命周期

每个插件经历 4 个阶段：

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐
│ on_load  │ → │ on_init  │ → │ 运行循环      │ → │on_unload │
│ 导入时    │    │ 初始化时  │    │ 钩子 + 节点   │    │ 卸载时    │
└──────────┘    └──────────┘    └──────────────┘    └──────────┘
```

### 2.1 on_load() → bool

**触发时机**：插件类被实例化并传入 `PluginManager.load()` 时立即触发。

**用途**：依赖检查、文件系统初始化、Python 版本检查。

**返回值**：`False` 阻止插件加载。

```python
def on_load(self) -> bool:
    # 检查必要依赖是否安装
    try:
        import requests
        return True
    except ImportError:
        print("此插件需要 requests 库: pip install requests")
        return False
```

### 2.2 on_init(config) → bool

**触发时机**：`on_load()` 成功之后，引擎启动之前。

**参数**：`config` — 用户传入的配置字典，可合并到 `self.settings`。

**用途**：读取配置、预热资源、建立数据库连接。

```python
def on_init(self, config: Optional[dict] = None) -> bool:
    if config:
        self.settings.update(config)
    # 预热 OCR 引擎（如果需要）
    if self.settings.get("preload_ocr"):
        from engine.vision import OCR
        OCR.instance().init()
    return True
```

### 2.3 运行循环

初始化完成后，插件进入运行状态。此阶段：

- 引擎级钩子（`on_start`、`on_pause`、`on_resume`、`on_stop`、`on_error`）由 `PluginManager` 主动调用。
- 节点级钩子（`pre_execute`、`post_execute`）自动注入到 `HookSystem`，随每个节点的执行触发。

### 2.4 on_unload()

**触发时机**：插件被卸载时（`PluginManager.unload("plugin_name")`）。

**用途**：释放资源、关闭连接、清理临时文件。

```python
def on_unload(self):
    # 关闭数据库连接
    if self._db_conn:
        self._db_conn.close()
    # 清理临时截图
    import shutil
    shutil.rmtree("/tmp/my_plugin_screenshots", ignore_errors=True)
```

---

## 3. BasePlugin 基类

### 3.1 类属性（子类必须/可选覆盖）

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `str` | ✅ | 插件唯一标识，建议 `snake_case` |
| `version` | `str` | ✅ | 版本号（SemVer） |
| `author` | `str` | 可选 | 作者署名 |
| `description` | `str` | 可选 | 一句话描述 |
| `default_settings` | `dict` | 可选 | 默认配置项字典 |

```python
class MyPlugin(BasePlugin):
    name = "auto_screenshot"
    version = "2.1.0"
    author = "张三"
    description = "执行失败时自动截图保存"

    default_settings = {
        "save_path": "./screenshots",
        "format": "png",
        "max_screenshots": 100,
    }
```

### 3.2 实例属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `settings` | `dict` | 当前配置（`default_settings` + 用户配置合并后） |
| `info` | `dict` (property) | 插件元信息字典 |

### 3.3 工具方法

#### get_setting(key, default=None)

读取配置项，支持点号路径访问嵌套字典。

```python
# 读取顶层配置
path = self.get_setting("save_path", "./default")

# 读取嵌套配置
threshold = self.get_setting("ocr.threshold", 0.8)
# 等价于 self.settings.get("ocr", {}).get("threshold", 0.8)
```

#### is_enabled() → bool

插件是否已启用（`on_init` 成功 + 未被禁用）。

```python
if self.is_enabled():
    self._do_work()
```

---

## 4. 七种生命周期钩子

### 概述

| 钩子 | 级别 | 触发时机 | 返回值 | 典型用途 |
|------|------|---------|--------|---------|
| `pre_execute` | 节点级 | 每个节点执行前 | `None` 或 `NodeResult` | 条件拦截、前置校验 |
| `post_execute` | 节点级 | 每个节点执行后 | 无 | 结果记录、后置校验 |
| `on_start` | 引擎级 | 脚本开始执行 | 无 | 初始化运行数据 |
| `on_pause` | 引擎级 | 脚本暂停 | 无 | 记录暂停快照 |
| `on_resume` | 引擎级 | 脚本恢复 | 无 | 恢复内部状态 |
| `on_stop` | 引擎级 | 脚本停止/结束 | 无 | 汇总统计、生成报告 |
| `on_error` | 引擎级 | 执行出错 | 无 | 错误上报、截图取证 |

### 4.1 pre_execute(node, ctx) → Optional[NodeResult]

**触发时机**：每个节点 `execute()` 调用之前。

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `node` | `BaseNode` | 即将执行的节点对象 |
| `ctx` | `ExecutionContext` | 当前执行上下文 |

**返回值**：
- `None` — 正常执行节点（默认行为）
- `NodeResult` — 跳过节点实际执行，直接将该结果作为节点返回值

**示例 — 按节点类型跳过执行**：

```python
def pre_execute(self, node, ctx):
    # 跳过所有等待节点（加速调试）
    if node.node_type == "wait":
        ctx.info(f"[加速模式] 跳过等待: {node.node_id}", node.node_id)
        return NodeResult(status=NodeStatus.SKIPPED)
    return None
```

**示例 — 动态修改节点配置**：

```python
def pre_execute(self, node, ctx):
    # 根据上下文变量动态设置按键次数
    if node.node_type == "key_press":
        repeat = ctx.get_var("repeat_count", 1)
        node.config["count"] = repeat
    return None
```

### 4.2 post_execute(node, ctx, result)

**触发时机**：每个节点 `execute()` 完成之后（含钩子拦截的情况）。

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `node` | `BaseNode` | 已执行的节点对象 |
| `ctx` | `ExecutionContext` | 当前执行上下文 |
| `result` | `NodeResult` | 节点的执行结果 |

**示例 — 收集执行耗时**：

```python
import time

def __init__(self):
    super().__init__()
    self._node_times: dict = {}

def pre_execute(self, node, ctx):
    self._node_times[node.node_id] = time.time()
    return None

def post_execute(self, node, ctx, result):
    start = self._node_times.pop(node.node_id, None)
    if start:
        elapsed = (time.time() - start) * 1000
        ctx.info(f"[耗时] {node.node_id}: {elapsed:.1f}ms", node.node_id,
                 data={"elapsed_ms": elapsed})
```

### 4.3 on_start(ctx)

**触发时机**：`ScriptRunner.run()` 开始执行时。

> **注意**：此钩子由 `PluginManager.notify_start()` 触发，需在执行前主动调用。

```python
def on_start(self, ctx: ExecutionContext):
    self._round = 0
    ctx.set_var("plugin_start_time", time.time())
    ctx.info(f"[{self.name}] 脚本开始 — 版本 {self.version}")
```

### 4.4 on_pause(ctx)

**触发时机**：执行器调用 `ScriptRunner.pause()` 后。

> **注意**：此钩子由 `PluginManager.notify_pause()` 触发。

```python
def on_pause(self, ctx: ExecutionContext):
    # 保存当前状态快照
    self._paused_state = {
        "node": ctx.stats.get("current_node"),
        "variables": ctx.get_all_variables(),
        "time": time.time(),
    }
    ctx.info(f"[{self.name}] 已保存暂停快照")
```

### 4.5 on_resume(ctx)

**触发时机**：执行器调用 `ScriptRunner.resume()` 后。

> **注意**：此钩子由 `PluginManager.notify_resume()` 触发。

```python
def on_resume(self, ctx: ExecutionContext):
    pause_duration = time.time() - self._paused_state.get("time", time.time())
    ctx.info(f"[{self.name}] 暂停了 {pause_duration:.1f}s 后恢复")
```

### 4.6 on_stop(ctx)

**触发时机**：执行器调用 `ScriptRunner.stop()` 或流程正常结束时。

> **注意**：此钩子由 `PluginManager.notify_stop()` 触发。

```python
def on_stop(self, ctx: ExecutionContext):
    stats = ctx.stats
    report = (
        f"=== 执行报告 ===\n"
        f"总节点: {stats['executed_count']}\n"
        f"成功:   {stats['success_count']}\n"
        f"失败:   {stats['failed_count']}\n"
        f"耗时:   {stats['elapsed_ms']}ms"
    )
    ctx.info(report)
    # 保存报告到磁盘
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report)
```

### 4.7 on_error(ctx, error)

**触发时机**：节点或引擎抛出未捕获的异常时。

> **注意**：此钩子由 `PluginManager.notify_error()` 触发。

```python
def on_error(self, ctx: ExecutionContext, error: Exception):
    # 发送告警（示例）
    ctx.error(f"[{self.name}] 执行异常: {error}")
    # 自动截图
    try:
        from engine.vision import Screenshot
        img = Screenshot.capture()
        ctx.cache_screenshot(f"error_{int(time.time())}", img)
    except Exception:
        pass
```

---

## 5. 自定义节点注册

### 5.1 创建自定义节点

自定义节点必须继承 `BaseNode` 并实现两个核心方法：

```python
from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.executor.context import ExecutionContext

class MyCustomNode(BaseNode):
    """自定义节点示例"""

    node_type = "my_custom"  # 唯一节点类型标识

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        """核心逻辑：必须实现"""
        # 从配置读取参数
        param = self.config.get("param", "默认值")

        # 写入上下文
        ctx.set_var("my_output", param)

        # 返回结果
        return NodeResult(status=NodeStatus.SUCCESS, data={"result": param})

    def validate(self) -> bool:
        """可选覆盖：校验配置合法性"""
        return bool(self.node_id) and "param" in self.config
```

### 5.2 在插件中注册

在 `register_nodes()` 方法中返回节点类型映射：

```python
class MyPlugin(BasePlugin):
    name = "my_plugin"

    def register_nodes(self) -> dict:
        return {
            "my_custom": MyCustomNode,       # 类型名 → 类
            "http_request": HttpRequestNode,  # 可注册多个
        }
```

### 5.3 在流程中使用自定义节点

```python
# 通过 PluginManager 获取节点类
CustomClass = manager.get_node_class("my_custom")
node = CustomClass("node_1", {"param": "hello"})

# 加入节点图
nodes = {
    "start": StartNode("start"),
    "custom": node,
    "end": EndNode("end"),
}
nodes["start"].next_nodes = ["custom"]
nodes["custom"].next_nodes = ["end"]
```

---

## 6. 插件配置系统

### 6.1 定义默认配置

```python
class MyPlugin(BasePlugin):
    default_settings = {
        "api": {
            "base_url": "http://localhost:8080",
            "timeout": 30,
        },
        "features": {
            "auto_screenshot": True,
            "retry_on_error": False,
        },
        "threshold": 0.85,
    }
```

### 6.2 初始化时合并用户配置

```python
def on_init(self, config: Optional[dict] = None) -> bool:
    if config:
        # config 深度合并到 self.settings
        self._deep_merge(self.settings, config)
    return True
```

### 6.3 运行时读取配置

```python
# 读取顶层设置
timeout = self.get_setting("api.timeout", 30)

# 读取嵌套设置
base_url = self.get_setting("api.base_url", "http://localhost:8080")

# 条件判断
if self.get_setting("features.auto_screenshot"):
    self._take_screenshot(ctx)
```

### 6.4 通过 API 传递配置

插件的 `PluginManager` 集成允许通过后端 API 传递插件配置。在 `PluginManager.load()` 之前调用 `plugin.on_init(config)`：

```python
plugin = MyPlugin()
plugin.on_init({
    "api": {"timeout": 60},
    "features": {"auto_screenshot": False},
})
manager.load(plugin)
```

---

## 7. PluginManager 管理器

### 7.1 核心 API

```python
from engine.plugin.base import PluginManager

manager = PluginManager()
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `manager.load(plugin)` | 加载插件 | `bool`（成功/失败） |
| `manager.unload(name)` | 卸载插件 | `None` |
| `manager.get(name)` | 按名称查找 | `BasePlugin` 或 `None` |
| `manager.list_all()` | 列出所有已加载插件 | `list[BasePlugin]` |
| `manager.get_node_class(type)` | 获取自定义节点类 | `Type[BaseNode]` 或 `None` |
| `manager.hook_system` | 获取合并钩子系统 | `HookSystem` |
| `manager.custom_node_types` | 所有注册的节点类型 | `dict` |

### 7.2 生命周期通知

由执行器或后端在适当时机调用：

```python
# 引擎级事件通知
await manager.notify_start(ctx)       # 脚本开始
await manager.notify_pause(ctx)       # 脚本暂停
await manager.notify_resume(ctx)      # 脚本恢复
await manager.notify_stop(ctx)        # 脚本停止
await manager.notify_error(ctx, e)    # 执行出错
```

### 7.3 与 ScriptRunner 集成

```python
from engine.executor.runner import ScriptRunner
from engine.plugin.base import PluginManager

# 1. 创建管理器并加载插件
manager = PluginManager()
manager.load(MyPluginA())
manager.load(MyPluginB())

# 2. 创建执行器，注入插件钩子
runner = ScriptRunner(
    nodes=nodes,
    hooks=manager.hook_system,  # ← 关键：注入合并后的钩子
)

# 3. 通知插件开始
ctx = ExecutionContext()
await manager.notify_start(ctx)

# 4. 执行
result_ctx = await runner.run()

# 5. 通知插件结束
await manager.notify_stop(result_ctx)
```

---

## 8. 端到端教程

本节从零开始，带你创建一个完整的「自动报告」插件。

### 8.1 需求

每次脚本执行完成后，自动生成一份 Markdown 格式的执行报告，包含：

- 执行节点数和成功率
- 每个节点的耗时
- 失败节点的错误信息

### 8.2 创建自定义节点

`report/nodes.py`：

```python
from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.executor.context import ExecutionContext

class ReportMarkerNode(BaseNode):
    """标记节点 — 在报告中插入自定义段落"""
    node_type = "report_marker"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        title = self.config.get("title", "未命名段落")
        # 追加到报告数据中
        markers = ctx.get_var("_report_markers", [])
        markers.append({"title": title, "time": ctx.stats.get("elapsed_ms", 0)})
        ctx.set_var("_report_markers", markers)
        ctx.info(f"[报告] 标记段落: {title}", self.node_id)
        return NodeResult(status=NodeStatus.SUCCESS)
```

### 8.3 创建插件主类

`report/plugin.py`：

```python
import time
from engine.plugin.base import BasePlugin
from engine.nodes.base import NodeResult, NodeStatus

class AutoReportPlugin(BasePlugin):
    name = "auto_report"
    version = "1.0.0"
    author = "你的名字"
    description = "脚本执行完成后自动生成 Markdown 报告"

    default_settings = {
        "output_dir": "./reports",
        "include_node_details": True,
        "report_title": "执行报告",
    }

    def __init__(self):
        super().__init__()
        self._node_records: list = []
        self._start_time: float = 0

    # ── 生命周期 ──
    def on_start(self, ctx):
        self._node_records.clear()
        self._start_time = time.time()

    def on_stop(self, ctx):
        self._generate_report(ctx)

    # ── 节点钩子 ──
    def pre_execute(self, node, ctx):
        # 记录开始时间
        ctx.set_var(f"_time_{node.node_id}", time.time())
        return None

    def post_execute(self, node, ctx, result):
        start = ctx.get_var(f"_time_{node.node_id}")
        elapsed = (time.time() - start) * 1000 if start else 0
        self._node_records.append({
            "id": node.node_id,
            "type": node.node_type,
            "status": result.status.value,
            "error": result.error or "",
            "elapsed_ms": round(elapsed, 1),
        })

    def on_error(self, ctx, error):
        # 记录未捕获的错误
        self._node_records.append({
            "id": ctx.stats.get("current_node", "?"),
            "type": "ERROR",
            "status": "error",
            "error": str(error),
            "elapsed_ms": 0,
        })

    # ── 节点注册 ──
    def register_nodes(self) -> dict:
        from report.nodes import ReportMarkerNode
        return {"report_marker": ReportMarkerNode}

    # ── 报告生成 ──
    def _generate_report(self, ctx):
        import os
        output_dir = self.get_setting("output_dir", "./reports")
        os.makedirs(output_dir, exist_ok=True)

        stats = ctx.stats
        total = len(self._node_records)
        success = sum(1 for r in self._node_records if r["status"] == "success")

        lines = [
            f"# {self.get_setting('report_title', '执行报告')}",
            "",
            f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**成功率**: {success}/{total} ({success/total*100:.0f}%)" if total else "",
            f"**总耗时**: {stats.get('elapsed_ms', 0)}ms",
            "",
            "## 节点明细",
            "",
            "| # | 节点 | 类型 | 状态 | 耗时 | 错误 |",
            "|---|------|------|------|------|------|",
        ]

        for i, r in enumerate(self._node_records, 1):
            status = "✅" if r["status"] == "success" else "❌"
            lines.append(
                f"| {i} | {r['id']} | {r['type']} | {status} "
                f"| {r['elapsed_ms']}ms | {r['error']} |"
            )

        # 追加自定义标记段落
        markers = ctx.get_var("_report_markers", [])
        if markers:
            lines.append("")
            lines.append("## 自定义段落")
            for m in markers:
                lines.append(f"- **{m['title']}** (at {m['time']}ms)")

        filename = os.path.join(
            output_dir,
            f"report_{time.strftime('%Y%m%d_%H%M%S')}.md",
        )
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        ctx.info(f"[AutoReport] 报告已保存: {filename}")
```

### 8.4 使用插件

```python
import asyncio
from engine.executor.runner import ScriptRunner
from engine.plugin.base import PluginManager
from engine.nodes.flow import StartNode, EndNode, WaitNode

async def main():
    # 加载插件
    manager = PluginManager()
    plugin = AutoReportPlugin()
    plugin.on_init({"output_dir": "./my_reports"})
    manager.load(plugin)

    # 构建流程
    nodes = {
        "start": StartNode("start"),
        "wait_a": WaitNode("wait_a", {"duration": 0.5}),
        "mark": manager.get_node_class("report_marker")(
            "mark", {"title": "第一阶段完成"}
        ),
        "wait_b": WaitNode("wait_b", {"duration": 0.3}),
        "end": EndNode("end"),
    }
    nodes["start"].next_nodes = ["wait_a"]
    nodes["wait_a"].next_nodes = ["mark"]
    nodes["mark"].next_nodes = ["wait_b"]
    nodes["wait_b"].next_nodes = ["end"]

    # 创建执行器
    runner = ScriptRunner(nodes, hooks=manager.hook_system)

    # 通知开始
    ctx = runner.context or __import__('engine.executor.context',
                                        fromlist=['ExecutionContext']).ExecutionContext()
    await manager.notify_start(ctx)

    # 执行
    result_ctx = await runner.run()

    # 通知结束 → 触发报告生成
    await manager.notify_stop(result_ctx)

    print("完成！查看 ./my_reports/ 目录")

asyncio.run(main())
```

---

## 9. API 参考速查

### BaseNode

```python
class BaseNode(ABC):
    node_type: str                    # 节点类型标识（子类覆盖）
    node_id: str                      # 节点唯一 ID
    config: dict                      # 节点配置
    next_nodes: list[str]             # 默认后续节点列表
    condition: Optional[str]          # 条件表达式

    async def execute(self, ctx: ExecutionContext) -> NodeResult  # ★ 必须实现
    def validate(self) -> bool                                      # 可选覆盖
    def get_next_node(self, result: NodeResult) -> Optional[str]    # 可选覆盖
    def to_dict(self) -> dict                                       # 序列化
```

### NodeResult

```python
@dataclass
class NodeResult:
    status: NodeStatus      # SUCCESS | FAILED | SKIPPED | WAITING
    data: Any = None        # 节点输出数据
    error: Optional[str]    # 错误信息
    next_node: Optional[str]# 覆盖默认下一个节点
```

### ExecutionContext（常用方法）

```python
class ExecutionContext:
    # 变量读写
    def get_var(key, default=None) -> Any
    def set_var(key, value)
    def get_all_variables() -> dict

    # 节点输出
    def get_node_output(node_id) -> Any
    def set_node_output(node_id, value)

    # 截图缓存
    def cache_screenshot(key, image)
    def get_screenshot(key) -> Any

    # 日志
    def info(message, node_id="", data=None)
    def warn(message, node_id="", data=None)
    def error(message, node_id="", data=None)
    def get_logs() -> list[dict]

    # 统计
    stats: dict  # executed_count, success_count, failed_count, elapsed_ms, current_node
```

### HookSystem

```python
class HookSystem:
    def on_pre_execute(hook: Callable)    # 注册 pre_execute 钩子
    def on_post_execute(hook: Callable)   # 注册 post_execute 钩子
    def remove_pre_hook(hook)             # 移除 pre_execute 钩子
    def remove_post_hook(hook)            # 移除 post_execute 钩子
    def clear()                           # 清空所有钩子
```

### PluginManager

```python
class PluginManager:
    def load(plugin: BasePlugin) -> bool
    def unload(plugin_name: str)
    def get(name: str) -> Optional[BasePlugin]
    def list_all() -> list[BasePlugin]
    def get_node_class(node_type: str) -> Optional[Type[BaseNode]]

    hook_system: HookSystem               # 属性：合并的钩子系统
    custom_node_types: dict               # 属性：所有注册的节点类型

    async def notify_start(ctx)
    async def notify_pause(ctx)
    async def notify_resume(ctx)
    async def notify_stop(ctx)
    async def notify_error(ctx, error)
```

---

## 附录 A：钩子触发时序图

```
ScriptRunner.run()
    │
    ├─ PluginManager.notify_start(ctx)      # ← on_start()
    │
    ├─ 执行循环开始
    │   │
    │   ├─ 节点 N
    │   │   ├─ HookSystem.run_pre_hooks()   # ← pre_execute() × N
    │   │   ├─ node.execute(ctx)            # 实际执行
    │   │   └─ HookSystem.run_post_hooks()  # ← post_execute() × N
    │   │
    │   ├─ (暂停)
    │   │   └─ PluginManager.notify_pause() # ← on_pause()
    │   │
    │   ├─ (恢复)
    │   │   └─ PluginManager.notify_resume()# ← on_resume()
    │   │
    │   └─ (异常)
    │       └─ PluginManager.notify_error() # ← on_error()
    │
    └─ PluginManager.notify_stop(ctx)       # ← on_stop()
```

## 附录 B：常见问题

**Q: 多个插件的 pre_execute 钩子执行顺序？**

按 `PluginManager.load()` 的加载顺序依次执行。任一返回 `NodeResult` 即短路，后续钩子不再执行。

**Q: 钩子中抛出异常会怎样？**

被 `HookSystem` 和 `PluginManager` 捕获，记录为 `WARN` 日志，不影响其他插件和脚本执行。

**Q: 可以在钩子中修改 ExecutionContext 的变量吗？**

可以。`ctx.set_var()` 在任意钩子中均可安全调用。

**Q: 自定义节点如何获取插件配置？**

自定义节点不知道自己属于哪个插件。如需共享配置，在 `pre_execute` 钩子中将配置写入上下文变量：

```python
def pre_execute(self, node, ctx):
    ctx.set_var("plugin_settings", self.settings)
    return None
```

然后在节点的 `execute()` 中：`settings = ctx.get_var("plugin_settings", {})`。
