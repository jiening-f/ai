"""Hello World 示例插件

展示插件开发的基本要素：
1. 继承 BasePlugin 并设置元信息
2. 覆盖生命周期方法
3. 使用 7 种钩子
4. 注册自定义节点类型
5. 读取插件配置
"""

import time
from typing import Optional

from engine.executor.context import ExecutionContext
from engine.nodes.base import BaseNode, NodeResult, NodeStatus
from engine.plugin.base import BasePlugin


# ═══════════════════════════════════════════════
# 自定义节点：HelloWorldNode
# ═══════════════════════════════════════════════

class HelloWorldNode(BaseNode):
    """示例自定义节点 — 输出问候语并可选地等待

    配置项:
        greeting: 问候语文本（默认 "你好，世界！"）
        wait_seconds: 执行后等待秒数（默认 0，不等待）
    """

    node_type = "hello_world"

    async def execute(self, ctx: ExecutionContext) -> NodeResult:
        greeting = self.config.get("greeting", "你好，世界！")
        name = ctx.get_var("user_name", "用户")
        wait_seconds = float(self.config.get("wait_seconds", 0))

        # 输出问候日志
        ctx.info(f"[HelloWorld] {greeting} — 欢迎 {name}!", self.node_id)

        # 将问候语存入上下文，供后续节点使用
        ctx.set_var("last_greeting", f"{greeting} — {name}")

        # 可选等待
        if wait_seconds > 0:
            import asyncio
            ctx.info(f"[HelloWorld] 等待 {wait_seconds}s", self.node_id)
            await asyncio.sleep(min(wait_seconds, 10))

        return NodeResult(status=NodeStatus.SUCCESS, data={"greeting": greeting, "user": name})

    def validate(self) -> bool:
        return bool(self.node_id)


# ═══════════════════════════════════════════════
# HelloWorldPlugin
# ═══════════════════════════════════════════════

class HelloWorldPlugin(BasePlugin):
    """Hello World 示例插件

    演示内容:
      - 7 种生命周期钩子的使用
      - 自定义节点注册
      - 插件配置读取
      - 执行统计收集
    """

    # ── 元信息 ──
    name = "hello_world"
    version = "1.0.0"
    author = "示例开发者"
    description = "一个演示插件开发基础的示例插件"

    # ── 默认配置 ──
    default_settings = {
        "greeting": "你好，世界！",
        "log_enabled": True,
        "collect_stats": True,
        "error_screenshot": False,
    }

    def __init__(self):
        super().__init__()
        self._start_time: float = 0
        self._node_count: int = 0
        self._error_count: int = 0

    # ═══════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════

    def on_load(self) -> bool:
        """加载时：打印版本信息"""
        if self.get_setting("log_enabled"):
            print(f"[HelloWorld] 插件 v{self.version} 已加载")
        return True

    def on_init(self, config: Optional[dict] = None) -> bool:
        """初始化时：合并用户配置"""
        if config:
            self.settings.update(config)
        self._start_time = 0
        self._node_count = 0
        self._error_count = 0
        if self.get_setting("log_enabled"):
            print(f"[HelloWorld] 初始化完成，配置: {self.settings}")
        return True

    def on_unload(self):
        """卸载时：输出运行统计"""
        if self.get_setting("log_enabled"):
            print(f"[HelloWorld] 插件卸载 — 共执行 {self._node_count} 个节点, "
                  f"错误 {self._error_count} 次")

    # ═══════════════════════════════════════════
    # 引擎级钩子
    # ═══════════════════════════════════════════

    def on_start(self, ctx: ExecutionContext):
        """引擎开始 — 记录开始时间，写入启动日志"""
        self._start_time = time.time()
        self._node_count = 0
        self._error_count = 0
        greeting = self.get_setting("greeting", "你好，世界！")
        ctx.info(f"[HelloWorld] {greeting} — 脚本开始执行")

    def on_pause(self, ctx: ExecutionContext):
        """引擎暂停 — 记录暂停点"""
        current = ctx.stats.get("current_node", "?")
        ctx.info(f"[HelloWorld] 脚本已暂停 (当前节点: {current})")

    def on_resume(self, ctx: ExecutionContext):
        """引擎恢复 — 记录恢复点"""
        current = ctx.stats.get("current_node", "?")
        ctx.info(f"[HelloWorld] 脚本已恢复 (当前节点: {current})")

    def on_stop(self, ctx: ExecutionContext):
        """引擎停止 — 输出运行摘要"""
        elapsed = time.time() - self._start_time if self._start_time else 0
        stats = ctx.stats
        ctx.info(
            f"[HelloWorld] 脚本结束 — "
            f"执行 {stats.get('executed_count', 0)} 个节点, "
            f"成功 {stats.get('success_count', 0)}, "
            f"失败 {stats.get('failed_count', 0)}, "
            f"耗时 {elapsed:.1f}s"
        )

    def on_error(self, ctx: ExecutionContext, error: Exception):
        """执行错误 — 计数并记录"""
        self._error_count += 1
        ctx.warn(f"[HelloWorld] 捕获错误: {error}")

        # 如果配置了错误截图（需要视觉模块）
        if self.get_setting("error_screenshot", False):
            try:
                from engine.vision import Screenshot
                img = Screenshot.capture()
                ctx.cache_screenshot(f"error_{self._error_count}", img)
                ctx.info(f"[HelloWorld] 已保存错误截图 #{self._error_count}")
            except Exception:
                ctx.warn("[HelloWorld] 截图失败（视觉模块不可用）")

    # ═══════════════════════════════════════════
    # 节点级钩子
    # ═══════════════════════════════════════════

    def pre_execute(self, node: BaseNode, ctx: ExecutionContext) -> Optional[NodeResult]:
        """节点执行前 — 计数并打印即将执行的节点"""
        self._node_count += 1
        if self.get_setting("log_enabled"):
            ctx.info(f"[HelloWorld] 即将执行 #{self._node_count}: {node}", node.node_id)
        return None  # 不拦截，正常执行

    def post_execute(self, node: BaseNode, ctx: ExecutionContext, result: NodeResult):
        """节点执行后 — 记录执行结果"""
        if self.get_setting("log_enabled"):
            status_icon = "✅" if result.status == NodeStatus.SUCCESS else "❌"
            ctx.info(
                f"[HelloWorld] {status_icon} 节点完成: {node} → {result.status.value}",
                node.node_id,
            )

    # ═══════════════════════════════════════════
    # 节点注册
    # ═══════════════════════════════════════════

    def register_nodes(self) -> dict:
        """注册 hello_world 自定义节点类型"""
        return {"hello_world": HelloWorldNode}


# ═══════════════════════════════════════════════
# 使用示例（可直接运行测试）
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    """运行方式:
        cd ai && python -m engine.plugin.examples.hello_world
    """
    import asyncio
    from engine.executor.runner import ScriptRunner
    from engine.plugin.base import PluginManager

    async def demo():
        # 1. 创建插件管理器并加载 hello_world 插件
        manager = PluginManager()
        plugin = HelloWorldPlugin()
        plugin.on_init({"greeting": "你好，全能脚本！"})
        manager.load(plugin)

        # 2. 构建包含自定义节点的流程
        nodes = {
            "start": HelloWorldNode("start", {"greeting": "插件演示开始"}),
            "hello": HelloWorldNode("hello", {
                "greeting": "这是通过自定义节点输出的问候语",
                "wait_seconds": 0.5,
            }),
        }
        nodes["start"].next_nodes = ["hello"]

        # 3. 创建执行器并注入插件钩子
        runner = ScriptRunner(nodes, start_node_id="start", hooks=manager.hook_system)

        # 4. 执行
        ctx = await runner.run()

        # 5. 通知插件生命周期
        await manager.notify_start(ctx)
        await manager.notify_stop(ctx)

        # 6. 输出日志
        print("\n执行日志:")
        for log in ctx.get_logs():
            # 清理 emoji 以兼容 Windows GBK 终端
            msg = log['message'].encode('gbk', errors='replace').decode('gbk', errors='replace')
            print(f"  [{log['level']}] {msg}")

    asyncio.run(demo())
