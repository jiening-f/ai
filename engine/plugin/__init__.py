"""插件系统 — 可扩展的第三方插件架构

提供 BasePlugin 基类和 PluginManager 管理器，
支持自定义节点注册和生命周期钩子。
"""

from engine.plugin.base import BasePlugin, PluginManager

__all__ = ["BasePlugin", "PluginManager"]
