## 任务：引擎节点定义

### 目标
定义 19 种脚本节点的基类和类型注册系统，为后续引擎开发奠定基础。

### 工作目录
`engine/`

### 要求

1. **节点基类 (`nodes/base.py`)**
   ```python
   class BaseNode:
       node_id: str
       node_type: str
       config: dict
       next_nodes: list[str]
       condition: str | None  # 条件表达式（条件节点用）

       async def execute(self, ctx: ExecutionContext) -> NodeResult
       def validate(self) -> bool
   ```

2. **执行上下文 (`executor/context.py`)**
   - 变量存储（dict）
   - 当前截图缓存
   - 运行状态（running/paused/stopped）
   - 日志收集

3. **19 种节点类型**
   | 分类 | 节点类型（node_type） | 说明 |
   |------|----------------------|------|
   | 流程控制 | start, end, wait, condition, loop | |
   | 键盘 | key_press, key_combo, key_hold | |
   | 鼠标 | mouse_click, mouse_dblclick, mouse_right, mouse_drag, mouse_scroll | |
   | 视觉 | ocr_recognize, template_match, screenshot | |
   | 数据 | variable_set, text_output | |

4. **节点注册表 (`nodes/registry.py`)**
   - NODE_REGISTRY: dict[str, type[BaseNode]]
   - register_node(type: str, cls: type) — 注册节点
   - get_node_class(type: str) — 获取节点类
   - list_node_types() — 列出所有节点类型（含名称、分类、描述）

5. **产出文件**
   ```
   engine/
   ├── __init__.py
   ├── executor/
   │   ├── __init__.py
   │   └── context.py          # 执行上下文
   ├── nodes/
   │   ├── __init__.py
   │   ├── base.py             # BaseNode + NodeResult
   │   ├── flow.py             # start, end, wait, condition, loop
   │   ├── keyboard.py         # key_press, key_combo, key_hold
   │   ├── mouse.py            # mouse_click, dblclick, right, drag, scroll
   │   ├── vision.py           # ocr_recognize, template_match, screenshot
   │   ├── data.py             # variable_set, text_output
   │   └── registry.py         # 节点注册表 + 元数据
   ├── vision/
   │   └── __init__.py         # 占位
   ├── input/
   │   └── __init__.py         # 占位
   ├── window/
   │   └── __init__.py         # 占位
   └── plugin/
       └── __init__.py         # 占位
   ```

6. **验证**
   - `from engine.nodes.registry import NODE_REGISTRY` 无报错
   - `len(NODE_REGISTRY) == 19`
   - 所有节点类 `validate()` 方法可调用
   - 每个节点类定义默认 config schema

### 参考架构
详见 `docs/architecture.md` 第四节 4.1 脚本引擎设计。
