"""插件基类与插件管理器 — 插件生命周期、钩子注册、节点扩展"""

from __future__ import annotations
from typing import Any, Optional, Type

from engine.executor.context import ExecutionContext
from engine.executor.hooks import HookSystem
from engine.nodes.base import BaseNode, NodeResult


class BasePlugin:
    """插件基类 — 所有第三方插件必须继承此类

    生命周期:
        on_load() → on_init() → [注册钩子+节点] → 运行循环 → on_unload()

    用法:
        class MyPlugin(BasePlugin):
            name = "my_plugin"
            version = "1.0.0"

            def on_init(self, config: dict) -> bool:
                self.settings.update(config)
                return True

            def pre_execute(self, node, ctx):
                ctx.info(f"即将执行: {node.node_id}")

            def register_nodes(self) -> dict:
                return {"my_custom": MyCustomNode}
    """

    # ── 元信息（子类必须覆盖） ──

    name: str = ""
    """插件名称（唯一标识，建议 snake_case）"""

    version: str = "1.0.0"
    """插件版本号（SemVer）"""

    author: str = ""
    """插件作者"""

    description: str = ""
    """插件描述"""

    # ── 默认配置 ──

    default_settings: dict = {}
    """插件默认配置项，子类可覆盖"""

    def __init__(self):
        self.settings: dict = dict(self.default_settings)
        self._enabled: bool = True
        self._initialized: bool = False
        self._hooks: Optional[HookSystem] = None

    # ═══════════════════════════════════════════
    # 生命周期方法（子类按需覆盖）
    # ═══════════════════════════════════════════

    def on_load(self) -> bool:
        """插件被加载到内存时调用（导入后立即触发）

        返回 False 可阻止插件加载。
        适合做：依赖检查、文件系统初始化。
        """
        return True

    def on_init(self, config: Optional[dict] = None) -> bool:
        """插件初始化时调用（引擎启动前）

        参数:
            config: 用户配置字典，可合并到 self.settings

        返回 False 可阻止插件启用。
        适合做：读取配置、预热资源、建立连接。
        """
        if config:
            self.settings.update(config)
        self._initialized = True
        return True

    def on_unload(self):
        """插件卸载时调用

        适合做：释放资源、关闭连接、清理临时文件。
        """
        self._initialized = False

    # ═══════════════════════════════════════════
    # 引擎级生命周期钩子（7 种）
    # ═══════════════════════════════════════════

    def on_start(self, ctx: ExecutionContext):
        """引擎开始执行时触发

        触发时机: ScriptRunner.run() 开始时
        参数:
            ctx: 执行上下文（可读写变量、写日志）
        用途: 初始化运行级数据、打印启动横幅
        """
        pass

    def on_pause(self, ctx: ExecutionContext):
        """引擎暂停时触发

        触发时机: ScriptRunner.pause() 调用后
        参数:
            ctx: 执行上下文
        用途: 记录暂停快照、通知外部系统
        """
        pass

    def on_resume(self, ctx: ExecutionContext):
        """引擎从暂停恢复时触发

        触发时机: ScriptRunner.resume() 调用后
        参数:
            ctx: 执行上下文
        用途: 恢复插件内部状态
        """
        pass

    def on_stop(self, ctx: ExecutionContext):
        """引擎停止时触发

        触发时机: ScriptRunner.stop() 调用后、或流程正常结束
        参数:
            ctx: 执行上下文（含完整执行历史）
        用途: 汇总统计、生成报告、清理运行级数据
        """
        pass

    def on_error(self, ctx: ExecutionContext, error: Exception):
        """引擎/节点执行出错时触发

        触发时机: 节点执行抛出异常、或引擎级错误
        参数:
            ctx: 执行上下文
            error: 异常对象
        用途: 错误上报、自动截图取证、告警通知
        """
        pass

    # ═══════════════════════════════════════════
    # 节点级钩子（线程安全、同步回调）
    # ═══════════════════════════════════════════

    def pre_execute(self, node: BaseNode, ctx: ExecutionContext) -> Optional[NodeResult]:
        """节点执行前钩子

        触发时机: 每个节点 execute() 调用前
        参数:
            node: 即将执行的节点对象
            ctx:  执行上下文
        返回:
            None → 正常执行节点
            NodeResult → 跳过节点执行，直接使用此结果

        用途: 条件拦截、前置校验、动态修改节点配置
        """
        return None

    def post_execute(self, node: BaseNode, ctx: ExecutionContext, result: NodeResult):
        """节点执行后钩子

        触发时机: 每个节点 execute() 完成后
        参数:
            node:   已执行的节点对象
            ctx:    执行上下文
            result: 节点执行结果

        用途: 结果记录、自定义统计、后置校验
        """
        pass

    # ═══════════════════════════════════════════
    # 节点注册
    # ═══════════════════════════════════════════

    def register_nodes(self) -> dict[str, Type[BaseNode]]:
        """注册自定义节点类型

        返回:
            {"node_type": NodeClass} 映射字典

        用法:
            def register_nodes(self):
                return {"screenshot": ScreenshotNode, "http_request": HttpNode}
        """
        return {}

    # ═══════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════

    def get_setting(self, key: str, default: Any = None) -> Any:
        """读取插件配置项（支持点号路径，如 'threshold.min'）"""
        keys = key.split(".")
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def is_enabled(self) -> bool:
        """插件是否已启用"""
        return self._enabled and self._initialized

    @property
    def info(self) -> dict:
        """插件元信息字典"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "enabled": self.is_enabled(),
        }


# ═══════════════════════════════════════════════
# 插件管理器
# ═══════════════════════════════════════════════

class PluginManager:
    """插件管理器 — 负责插件的加载、初始化、钩子分发和卸载

    用法:
        manager = PluginManager()
        manager.load(MyPlugin())
        manager.load(AnotherPlugin())

        # 注入到 ScriptRunner
        runner = ScriptRunner(nodes, hooks=manager.hook_system)

        # 生命周期通知
        await manager.notify_start(ctx)
        await manager.notify_stop(ctx)
    """

    def __init__(self):
        self._plugins: list[BasePlugin] = []
        self._node_registry: dict[str, Type[BaseNode]] = {}
        self._hook_system: Optional[HookSystem] = None

    # ── 插件管理 ──

    def load(self, plugin: BasePlugin) -> bool:
        """加载插件（导入 → on_load → on_init）

        返回 True 表示加载成功。
        """
        # 检查重名
        if any(p.name == plugin.name for p in self._plugins):
            return False

        # 阶段 1: on_load
        if not plugin.on_load():
            return False

        # 阶段 2: on_init
        if not plugin.on_init():
            return False

        self._plugins.append(plugin)

        # 注册自定义节点
        custom_nodes = plugin.register_nodes()
        for node_type, node_cls in custom_nodes.items():
            if node_type in self._node_registry:
                # 不覆盖已注册的类型
                continue
            self._node_registry[node_type] = node_cls

        # 注册钩子
        self._register_plugin_hooks(plugin)

        return True

    def unload(self, plugin_name: str):
        """卸载指定插件"""
        for plugin in self._plugins:
            if plugin.name == plugin_name:
                plugin.on_unload()
                self._plugins.remove(plugin)
                # 清理该插件注册的节点类型
                custom_nodes = plugin.register_nodes()
                for node_type in custom_nodes:
                    self._node_registry.pop(node_type, None)
                break

    def get(self, name: str) -> Optional[BasePlugin]:
        """按名称获取已加载的插件"""
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    def list_all(self) -> list[BasePlugin]:
        """列出所有已加载的插件"""
        return list(self._plugins)

    # ── 节点注册 ──

    def get_node_class(self, node_type: str) -> Optional[Type[BaseNode]]:
        """获取自定义节点类（含内置类型回退）"""
        return self._node_registry.get(node_type)

    @property
    def custom_node_types(self) -> dict[str, Type[BaseNode]]:
        """所有自定义节点类型映射"""
        return dict(self._node_registry)

    # ── 钩子系统 ──

    @property
    def hook_system(self) -> HookSystem:
        """获取合并了所有插件钩子的 HookSystem"""
        if self._hook_system is None:
            self._hook_system = HookSystem()
        return self._hook_system

    def _register_plugin_hooks(self, plugin: BasePlugin):
        """将插件的钩子方法注册到 HookSystem"""
        hs = self.hook_system

        # pre_execute — 有返回值则拦截
        def make_pre(plug):
            def pre(node, ctx):
                return plug.pre_execute(node, ctx)
            pre.__name__ = f"pre_{plug.name}"
            return pre

        hs.on_pre_execute(make_pre(plugin))

        # post_execute
        def make_post(plug):
            def post(node, ctx, result):
                plug.post_execute(node, ctx, result)
            post.__name__ = f"post_{plug.name}"
            return post

        hs.on_post_execute(make_post(plugin))

    # ── 生命周期通知 ──

    async def notify_start(self, ctx: ExecutionContext):
        """通知所有插件：引擎开始"""
        for p in self._plugins:
            if p.is_enabled():
                try:
                    p.on_start(ctx)
                except Exception as e:
                    ctx.warn(f"插件 {p.name} on_start 异常: {e}")

    async def notify_pause(self, ctx: ExecutionContext):
        """通知所有插件：引擎暂停"""
        for p in self._plugins:
            if p.is_enabled():
                try:
                    p.on_pause(ctx)
                except Exception as e:
                    ctx.warn(f"插件 {p.name} on_pause 异常: {e}")

    async def notify_resume(self, ctx: ExecutionContext):
        """通知所有插件：引擎恢复"""
        for p in self._plugins:
            if p.is_enabled():
                try:
                    p.on_resume(ctx)
                except Exception as e:
                    ctx.warn(f"插件 {p.name} on_resume 异常: {e}")

    async def notify_stop(self, ctx: ExecutionContext):
        """通知所有插件：引擎停止"""
        for p in self._plugins:
            if p.is_enabled():
                try:
                    p.on_stop(ctx)
                except Exception as e:
                    ctx.warn(f"插件 {p.name} on_stop 异常: {e}")

    async def notify_error(self, ctx: ExecutionContext, error: Exception):
        """通知所有插件：执行出错"""
        for p in self._plugins:
            if p.is_enabled():
                try:
                    p.on_error(ctx, error)
                except Exception as e:
                    ctx.warn(f"插件 {p.name} on_error 异常: {e}")
