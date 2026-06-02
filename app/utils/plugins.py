"""插件架构模块 -- 插件接口、发现、加载和生命周期管理。

提供标准化的插件接口，支持自动发现和加载外部插件。
插件可以扩展应用功能而不修改核心代码。

使用示例::

    from app.utils.plugins import PluginManager, Plugin

    # 自定义插件
    class MyPlugin(Plugin):
        @property
        def name(self) -> str:
            return "my-plugin"

        @property
        def version(self) -> str:
            return "1.0.0"

        def on_load(self, app) -> None:
            logger.info("插件已加载")

        def on_ready(self, app) -> None:
            logger.info("应用就绪")

    # 注册并启动
    pm = PluginManager()
    pm.register(MyPlugin())
    pm.load_all(app)
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plugin lifecycle states
# ---------------------------------------------------------------------------


class PluginState(Enum):
    """插件生命周期状态。"""

    REGISTERED = "registered"  # 已注册，尚未加载
    LOADING = "loading"  # 正在加载
    LOADED = "loaded"  # 已加载（on_load 完成）
    READY = "ready"  # 应用就绪（on_ready 完成）
    UNLOADING = "unloading"  # 正在卸载
    UNLOADED = "unloaded"  # 已卸载
    ERROR = "error"  # 出错


# ---------------------------------------------------------------------------
# Plugin interface
# ---------------------------------------------------------------------------


class Plugin(ABC):
    """插件抽象基类。

    所有插件必须继承此类并实现必要的属性和方法。
    生命周期顺序: on_load -> on_ready -> on_unload
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一名称。"""

    @property
    def version(self) -> str:
        """插件版本号。"""
        return "0.0.0"

    @property
    def description(self) -> str:
        """插件描述。"""
        return ""

    @property
    def author(self) -> str:
        """插件作者。"""
        return ""

    @property
    def dependencies(self) -> list[str]:
        """此插件依赖的其他插件名称列表。"""
        return []

    def on_load(self, app: Any) -> None:  # noqa: B027
        """插件加载时调用。

        在此阶段进行初始化、注册事件监听等。
        抛出异常将标记插件为 ERROR 状态。

        Args:
            app: 应用实例引用。
        """

    def on_ready(self, app: Any) -> None:  # noqa: B027
        """应用就绪后调用。

        所有插件加载完成后统一调用。适合进行需要其他插件就绪的操作。

        Args:
            app: 应用实例引用。
        """

    def on_unload(self, app: Any) -> None:  # noqa: B027
        """插件卸载时调用。

        在此阶段清理资源、退订事件等。

        Args:
            app: 应用实例引用。
        """

    def __repr__(self) -> str:
        return f"<Plugin '{self.name}' v{self.version} [{self._state.value if hasattr(self, '_state') else 'unknown'}]>"


# ---------------------------------------------------------------------------
# Plugin metadata
# ---------------------------------------------------------------------------


class PluginInfo:
    """插件运行时元信息。

    Attributes:
        plugin: 插件实例。
        state: 当前生命周期状态。
        error: 如果出错，存储异常信息。
    """

    __slots__ = ("plugin", "state", "error")

    def __init__(self, plugin: Plugin) -> None:
        self.plugin = plugin
        self.state: PluginState = PluginState.REGISTERED
        self.error: Optional[Exception] = None

    @property
    def name(self) -> str:
        return self.plugin.name

    @property
    def is_healthy(self) -> bool:
        return self.state not in (PluginState.ERROR, PluginState.UNLOADED)


# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------


def discover_plugins(directory: Path) -> list[Plugin]:
    """在指定目录中发现插件。

    扫描目录中的 .py 文件，导入并查找 Plugin 子类实例。

    Args:
        directory: 插件目录路径。

    Returns:
        发现的插件实例列表。
    """
    plugins: list[Plugin] = []

    if not directory.is_dir():
        logger.warning("插件目录不存在: %s", directory)
        return plugins

    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        try:
            module_name = f"_plugin_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            for _attr_name, obj in inspect.getmembers(module):
                # Plugin instance already created
                if isinstance(obj, Plugin) and not inspect.isabstract(type(obj)):
                    plugins.append(obj)
                    logger.info("发现插件: %s v%s (来自 %s)", obj.name, obj.version, py_file.name)
                # Plugin subclass -- try to instantiate it
                elif (
                    inspect.isclass(obj)
                    and issubclass(obj, Plugin)
                    and obj is not Plugin
                    and not inspect.isabstract(obj)
                ):
                    try:
                        instance = obj()
                        plugins.append(instance)
                        logger.info("发现插件: %s v%s (来自 %s)", instance.name, instance.version, py_file.name)
                    except Exception:
                        logger.debug("无法实例化插件类 %s", obj.__name__, exc_info=True)

        except Exception as exc:
            logger.error("加载插件文件 %s 失败: %s", py_file, exc, exc_info=True)

    return plugins


def discover_plugins_from_package(package_path: Path) -> list[Plugin]:
    """在 Python 包目录中发现插件。

    与 discover_plugins 类似，但处理 __init__.py 和子目录。

    Args:
        package_path: 包目录路径。

    Returns:
        发现的插件实例列表。
    """
    plugins: list[Plugin] = []

    if not package_path.is_dir():
        return plugins

    for item in sorted(package_path.iterdir()):
        if item.suffix == ".py" and not item.name.startswith("_"):
            plugins.extend(discover_plugins(item.parent))
            break
        elif item.is_dir() and (item / "__init__.py").exists():
            plugins.extend(discover_plugins(item))

    return plugins


# ---------------------------------------------------------------------------
# Plugin manager
# ---------------------------------------------------------------------------


class PluginManager:
    """插件管理器 -- 负责插件的注册、加载和生命周期管理。

    线程安全的操作顺序: register -> load_all -> (ready) -> unload_all

    Attributes:
        _plugins: 已注册的插件信息字典。
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._loaded: bool = False
        self._ready: bool = False

    def register(self, plugin: Plugin) -> None:
        """注册插件。

        Args:
            plugin: 插件实例。

        Raises:
            ValueError: 插件名称已注册。
        """
        if plugin.name in self._plugins:
            raise ValueError(f"插件 '{plugin.name}' 已注册")
        self._plugins[plugin.name] = PluginInfo(plugin)
        logger.debug("注册插件: %s v%s", plugin.name, plugin.version)

    def register_many(self, plugins: list[Plugin]) -> None:
        """批量注册插件。"""
        for plugin in plugins:
            try:
                self.register(plugin)
            except ValueError as exc:
                logger.warning("注册插件失败: %s", exc)

    def unregister(self, name: str) -> None:
        """注销插件。必须先卸载。"""
        info = self._plugins.get(name)
        if info is None:
            return
        if info.state not in (PluginState.REGISTERED, PluginState.UNLOADED):
            raise ValueError(f"插件 '{name}' 处于 {info.state.value} 状态，无法注销")
        del self._plugins[name]

    def get(self, name: str) -> Optional[Plugin]:
        """按名称获取插件实例。"""
        info = self._plugins.get(name)
        return info.plugin if info else None

    def get_info(self, name: str) -> Optional[PluginInfo]:
        """按名称获取插件信息。"""
        return self._plugins.get(name)

    def all_plugins(self) -> list[PluginInfo]:
        """返回所有已注册的插件信息。"""
        return list(self._plugins.values())

    def healthy_plugins(self) -> list[PluginInfo]:
        """返回状态健康的插件信息列表。"""
        return [info for info in self._plugins.values() if info.is_healthy]

    @property
    def count(self) -> int:
        """已注册插件数量。"""
        return len(self._plugins)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _resolve_load_order(self) -> list[PluginInfo]:
        """按依赖关系解析加载顺序（拓扑排序）。

        Returns:
            按依赖顺序排列的插件信息列表。

        Raises:
            RuntimeError: 存在循环依赖或缺失依赖。
        """
        name_to_info = {info.name: info for info in self._plugins.values()}
        visited: set[str] = set()
        order: list[PluginInfo] = []

        def visit(name: str, path: list[str]) -> None:
            if name in visited:
                return
            if name in path:
                raise RuntimeError(f"插件循环依赖: {' -> '.join(path)} -> {name}")
            if name not in name_to_info:
                raise RuntimeError(f"插件 '{name}' 未注册（被依赖但缺失）")
            path.append(name)
            for dep in name_to_info[name].plugin.dependencies:
                visit(dep, list(path))
            visited.add(name)
            order.append(name_to_info[name])

        for info_name in name_to_info:
            visit(info_name, [])

        return order

    def load_all(self, app: Any = None) -> list[str]:
        """按依赖顺序加载所有插件。

        调用每个插件的 on_load 方法。

        Args:
            app: 应用实例，传递给插件的生命周期方法。

        Returns:
            成功加载的插件名称列表。
        """
        loaded: list[str] = []
        try:
            order = self._resolve_load_order()
        except RuntimeError as exc:
            logger.error("插件依赖解析失败: %s", exc)
            return loaded

        for info in order:
            if info.state == PluginState.LOADED:
                loaded.append(info.name)
                continue

            info.state = PluginState.LOADING
            try:
                info.plugin.on_load(app)
                info.state = PluginState.LOADED
                loaded.append(info.name)
                logger.info("插件已加载: %s", info.name)
            except Exception as exc:
                info.state = PluginState.ERROR
                info.error = exc
                logger.error("插件 '%s' 加载失败: %s", info.name, exc, exc_info=True)

        self._loaded = True
        return loaded

    def ready_all(self, app: Any = None) -> list[str]:
        """对所有已加载的插件调用 on_ready。

        Args:
            app: 应用实例。

        Returns:
            成功就绪的插件名称列表。
        """
        ready_list: list[str] = []

        for info in self._plugins.values():
            if info.state != PluginState.LOADED:
                continue
            try:
                info.plugin.on_ready(app)
                info.state = PluginState.READY
                ready_list.append(info.name)
                logger.info("插件就绪: %s", info.name)
            except Exception as exc:
                info.state = PluginState.ERROR
                info.error = exc
                logger.error("插件 '%s' 就绪失败: %s", info.name, exc, exc_info=True)

        self._ready = True
        return ready_list

    def unload_all(self, app: Any = None) -> list[str]:
        """卸载所有插件（反序）。

        Args:
            app: 应用实例。

        Returns:
            已卸载的插件名称列表。
        """
        unloaded: list[str] = []

        # Reverse load order for proper unwinding
        try:
            order = list(reversed(self._resolve_load_order()))
        except RuntimeError:
            order = list(reversed(list(self._plugins.values())))

        for info in order:
            if info.state in (PluginState.REGISTERED, PluginState.UNLOADED):
                continue
            info.state = PluginState.UNLOADING
            try:
                info.plugin.on_unload(app)
                info.state = PluginState.UNLOADED
                unloaded.append(info.name)
                logger.info("插件已卸载: %s", info.name)
            except Exception as exc:
                info.state = PluginState.ERROR
                info.error = exc
                logger.error("插件 '%s' 卸载失败: %s", info.name, exc, exc_info=True)

        self._loaded = False
        self._ready = False
        return unloaded

    def load_from_directory(self, directory: Path, app: Any = None) -> list[str]:
        """从目录发现、注册并加载插件。

        Args:
            directory: 插件目录路径。
            app: 应用实例。

        Returns:
            成功加载的插件名称列表。
        """
        discovered = discover_plugins(directory)
        self.register_many(discovered)
        return self.load_all(app)

    def status_summary(self) -> dict:
        """返回所有插件的状态摘要。"""
        summary = {}
        for info in self._plugins.values():
            summary[info.name] = {
                "version": info.plugin.version,
                "state": info.state.value,
                "error": str(info.error) if info.error else None,
            }
        return summary
