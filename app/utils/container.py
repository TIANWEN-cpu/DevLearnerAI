"""依赖注入容器模块 -- 服务注册与懒解析。

提供轻量级的依赖注入容器，支持：
- 工厂函数注册（惰性构造）
- 实例注册（预构造）
- 单例模式（首次解析后缓存）
- 依赖关系自动解析

使用示例::

    from app.utils.container import Container

    container = Container()

    # 注册工厂（惰性构造，首次 resolve 时执行）
    container.register_factory("db", lambda: AppDatabase())

    # 注册实例（预构造的单例）
    container.register_instance("config", {"debug": True})

    # 注册为单例（工厂只执行一次，后续返回缓存）
    container.register_factory("db", lambda: AppDatabase(), singleton=True)

    # 解析
    db = container.resolve("db")

    # 依赖注入装饰器
    @inject
    def create_dashboard(db: AppDatabase = Depends("db")):
        return DashboardWidget(db)
"""

from __future__ import annotations

import inspect
import logging
import threading
from typing import Any, Callable, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_SENTINEL = object()


# ---------------------------------------------------------------------------
# Dependency descriptor (for decorator-based injection)
# ---------------------------------------------------------------------------


class Depends:
    """依赖描述符 -- 用于函数参数默认值，标记需要注入的依赖。

    使用示例::

        def my_func(db: AppDatabase = Depends("db")):
            ...
    """

    __slots__ = ("service_name", "default")

    def __init__(self, service_name: str, default: Any = _SENTINEL) -> None:
        self.service_name = service_name
        self.default = default

    def __repr__(self) -> str:
        return f"Depends('{self.service_name}')"


# ---------------------------------------------------------------------------
# Registration entry
# ---------------------------------------------------------------------------


class _Registration:
    """容器中的注册条目。"""

    __slots__ = ("factory", "instance", "singleton", "tags")

    def __init__(
        self,
        factory: Callable[..., Any] | None = None,
        instance: Any = _SENTINEL,
        singleton: bool = False,
        tags: list[str] | None = None,
    ) -> None:
        self.factory = factory
        self.instance = instance
        self.singleton = singleton
        self.tags = tags or []


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------


class Container:
    """依赖注入容器。

    支持工厂函数注册、实例注册、单例缓存和标签查询。
    线程安全。
    """

    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = threading.Lock()

    # ── Registration ───────────────────────────────────────────────────────

    def register_factory(
        self,
        name: str,
        factory: Callable[..., Any],
        singleton: bool = False,
        tags: list[str] | None = None,
    ) -> None:
        """注册工厂函数。

        Args:
            name: 服务名称（解析时的键）。
            factory: 工厂函数，调用时返回服务实例。
            singleton: 是否为单例（首次解析后缓存）。
            tags: 标签列表（用于批量查询）。
        """
        with self._lock:
            self._registrations[name] = _Registration(
                factory=factory,
                singleton=singleton,
                tags=tags,
            )
        logger.debug("注册工厂: %s (singleton=%s)", name, singleton)

    def register_instance(self, name: str, instance: Any, tags: list[str] | None = None) -> None:
        """注册预构造的实例（始终为单例）。

        Args:
            name: 服务名称。
            instance: 预构造的服务实例。
            tags: 标签列表。
        """
        with self._lock:
            self._registrations[name] = _Registration(instance=instance, tags=tags)
            self._singletons[name] = instance
        logger.debug("注册实例: %s (%s)", name, type(instance).__name__)

    def register_class(
        self,
        name: str,
        cls: Type[T],
        singleton: bool = True,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """注册类（通过调用类构造函数创建实例）。

        Args:
            name: 服务名称。
            cls: 类。
            singleton: 是否为单例。
            tags: 标签列表。
            **kwargs: 传递给构造函数的额外参数。
        """

        def factory() -> T:
            return cls(**kwargs)

        self.register_factory(name, factory, singleton=singleton, tags=tags)

    def unregister(self, name: str) -> None:
        """注销服务。

        Args:
            name: 服务名称。
        """
        with self._lock:
            self._registrations.pop(name, None)
            self._singletons.pop(name, None)

    # ── Resolution ─────────────────────────────────────────────────────────

    def resolve(self, name: str) -> Any:
        """解析服务。

        如果注册为单例且已缓存，返回缓存实例；
        否则调用工厂函数创建新实例。

        Args:
            name: 服务名称。

        Returns:
            服务实例。

        Raises:
            KeyError: 服务未注册。
        """
        with self._lock:
            # Check singleton cache first
            if name in self._singletons:
                return self._singletons[name]

            reg = self._registrations.get(name)
            if reg is None:
                raise KeyError(f"服务 '{name}' 未注册")

            # Instance registration (already in singletons by register_instance)
            if reg.instance is not _SENTINEL:
                return reg.instance

            if reg.factory is None:
                raise KeyError(f"服务 '{name}' 没有工厂函数")

        # Create outside lock to avoid holding it during construction
        instance = reg.factory()

        with self._lock:
            if reg.singleton:
                self._singletons[name] = instance

        logger.debug("解析服务: %s -> %s", name, type(instance).__name__)
        return instance

    def resolve_or_none(self, name: str) -> Any:
        """解析服务，未注册时返回 None 而不是抛出异常。"""
        try:
            return self.resolve(name)
        except KeyError:
            return None

    def resolve_or_default(self, name: str, default: Any = None) -> Any:
        """解析服务，未注册时返回默认值。"""
        try:
            return self.resolve(name)
        except KeyError:
            return default

    def resolve_type(self, name: str, expected_type: Type[T]) -> T:
        """解析服务并进行类型检查。

        Args:
            name: 服务名称。
            expected_type: 期望的类型。

        Returns:
            类型化的服务实例。

        Raises:
            TypeError: 实例类型不匹配。
        """
        instance = self.resolve(name)
        if not isinstance(instance, expected_type):
            raise TypeError(
                f"服务 '{name}' 的类型不匹配: 期望 {expected_type.__name__}，实际 {type(instance).__name__}"
            )
        return instance

    # ── Tag queries ────────────────────────────────────────────────────────

    def resolve_by_tag(self, tag: str) -> dict[str, Any]:
        """按标签解析所有匹配的服务。

        Args:
            tag: 标签名。

        Returns:
            {name: instance} 字典。
        """
        results = {}
        with self._lock:
            names = [name for name, reg in self._registrations.items() if tag in reg.tags]
        for name in names:
            try:
                results[name] = self.resolve(name)
            except Exception as exc:
                logger.warning("按标签解析服务 '%s' 失败: %s", name, exc)
        return results

    # ── Introspection ──────────────────────────────────────────────────────

    def is_registered(self, name: str) -> bool:
        """检查服务是否已注册。"""
        return name in self._registrations

    def registered_names(self) -> list[str]:
        """返回所有已注册的服务名称。"""
        return list(self._registrations.keys())

    def registered_count(self) -> int:
        """返回注册服务数量。"""
        return len(self._registrations)

    def cached_singleton_names(self) -> list[str]:
        """返回已缓存的单例名称。"""
        return list(self._singletons.keys())

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def clear(self) -> None:
        """清空容器（所有注册和缓存）。"""
        with self._lock:
            self._registrations.clear()
            self._singletons.clear()

    def reset_singletons(self) -> None:
        """重置所有单例缓存（不影响注册）。

        下次 resolve 时将重新创建实例。
        """
        with self._lock:
            self._singletons.clear()


# ---------------------------------------------------------------------------
# Injection decorator
# ---------------------------------------------------------------------------


# Global default container
_default_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局默认容器。

    如果不存在则自动创建。
    """
    global _default_container
    if _default_container is None:
        _default_container = Container()
    return _default_container


def set_container(container: Container) -> None:
    """设置全局默认容器。"""
    global _default_container
    _default_container = container


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    """装饰器：自动注入函数参数中的 Depends 默认值。

    使用示例::

        @inject
        def create_dashboard(db: AppDatabase = Depends("db")):
            return DashboardWidget(db)

        dashboard = create_dashboard()  # db 自动从容器解析
    """
    sig = inspect.signature(func)
    container = get_container()

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Fill in missing args from container
        for param_name, param in sig.parameters.items():
            if param_name in kwargs:
                continue
            if isinstance(param.default, Depends):
                dep = param.default
                resolved = container.resolve_or_default(dep.service_name, dep.default)
                if resolved is not _SENTINEL:
                    kwargs[param_name] = resolved
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__doc__ = func.__doc__
    wrapper.__signature__ = sig  # type: ignore[attr-defined]
    return wrapper
