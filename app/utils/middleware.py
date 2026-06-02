"""中间件模式模块 -- 请求处理管道。

提供可组合的中间件链，用于在函数调用前后执行横切关注点：
日志记录、错误处理、输入验证、性能监控等。

使用示例::

    from app.utils.middleware import MiddlewareChain, LoggingMiddleware, ErrorHandlingMiddleware

    chain = MiddlewareChain()
    chain.add(LoggingMiddleware())
    chain.add(ErrorHandlingMiddleware())

    @chain.wrap
    def save_note(lesson_id: str, content: str):
        db.save_note(lesson_id, content)

    save_note("py-01", "笔记内容")  # 自动记录日志 + 错误处理
"""

from __future__ import annotations

import functools
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, TypeVar

from app.utils.error_handler import log_error

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Middleware context
# ---------------------------------------------------------------------------


class MiddlewareContext:
    """中间件上下文，通过管道传递函数调用的元信息。

    Attributes:
        func_name: 被调用函数的限定名称。
        args: 位置参数。
        kwargs: 关键字参数。
        metadata: 中间件之间共享的附加元数据。
        result: 函数执行结果（在 after 阶段可用）。
        error: 函数执行异常（在 after 阶段可用，无异常则为 None）。
        elapsed_ms: 函数执行耗时（毫秒）。
    """

    __slots__ = ("func_name", "args", "kwargs", "metadata", "result", "error", "elapsed_ms")

    def __init__(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> None:
        self.func_name = func_name
        self.args = args
        self.kwargs = kwargs or {}
        self.metadata: dict[str, Any] = {}
        self.result: Any = None
        self.error: Optional[Exception] = None
        self.elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# Abstract base middleware
# ---------------------------------------------------------------------------


class Middleware(ABC):
    """中间件基类。

    子类应实现 before / after 方法。before 可抛出异常阻止执行，
    after 可检查 ctx.error 处理异常。
    """

    @abstractmethod
    def before(self, ctx: MiddlewareContext) -> None:
        """函数调用前执行。抛出异常将阻止函数执行。"""

    @abstractmethod
    def after(self, ctx: MiddlewareContext) -> None:
        """函数调用后执行。ctx.result 或 ctx.error 已就绪。"""


# ---------------------------------------------------------------------------
# Logging middleware
# ---------------------------------------------------------------------------


class LoggingMiddleware(Middleware):
    """日志记录中间件。

    记录函数调用的开始、结束和耗时。
    """

    def __init__(self, level: int = logging.DEBUG, log_args: bool = False) -> None:
        self._level = level
        self._log_args = log_args

    def before(self, ctx: MiddlewareContext) -> None:
        if self._log_args:
            logger.log(
                self._level,
                "[MW] 调用 %s(args=%s, kwargs=%s)",
                ctx.func_name,
                ctx.args,
                ctx.kwargs,
            )
        else:
            logger.log(self._level, "[MW] 调用 %s", ctx.func_name)

    def after(self, ctx: MiddlewareContext) -> None:
        if ctx.error:
            logger.warning(
                "[MW] %s 失败 (%.1fms): %s",
                ctx.func_name,
                ctx.elapsed_ms,
                ctx.error,
            )
        else:
            logger.log(
                self._level,
                "[MW] %s 完成 (%.1fms)",
                ctx.func_name,
                ctx.elapsed_ms,
            )


# ---------------------------------------------------------------------------
# Error handling middleware
# ---------------------------------------------------------------------------


class ErrorHandlingMiddleware(Middleware):
    """错误处理中间件。

    捕获函数执行中的异常，记录日志并决定是否吞没异常。
    """

    def __init__(
        self,
        swallow: bool = True,
        default: Any = None,
        reraise: bool = False,
    ) -> None:
        self._swallow = swallow
        self._default = default
        self._reraise = reraise

    def before(self, ctx: MiddlewareContext) -> None:
        pass  # no-op

    def after(self, ctx: MiddlewareContext) -> None:
        if ctx.error is None:
            return

        log_error(ctx.error, ctx.func_name)

        if self._reraise:
            raise ctx.error

        if self._swallow:
            ctx.result = self._default
            ctx.error = None


# ---------------------------------------------------------------------------
# Validation middleware
# ---------------------------------------------------------------------------


class ValidationRule:
    """单条验证规则。

    Args:
        name: 规则名称（用于错误消息）。
        check: 验证函数，接受函数参数，返回 True 表示通过。
        message: 验证失败时的错误消息。
        param_name: 关联的参数名（可选，用于定位具体参数）。
    """

    def __init__(
        self,
        name: str,
        check: Callable[..., bool],
        message: str,
        param_name: str = "",
    ) -> None:
        self.name = name
        self.check = check
        self.message = message
        self.param_name = param_name


class ValidationError(Exception):
    """验证中间件抛出的异常。"""

    def __init__(self, rule_name: str, message: str, param_name: str = "") -> None:
        self.rule_name = rule_name
        self.param_name = param_name
        super().__init__(message)


class ValidationMiddleware(Middleware):
    """输入验证中间件。

    在函数执行前检查参数是否满足指定规则。规则失败时抛出 ValidationError。
    """

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self._rules: list[ValidationRule] = list(rules or [])

    def add_rule(self, rule: ValidationRule) -> None:
        """添加验证规则。"""
        self._rules.append(rule)

    def before(self, ctx: MiddlewareContext) -> None:
        for rule in self._rules:
            try:
                if not rule.check(*ctx.args, **ctx.kwargs):
                    raise ValidationError(rule.name, rule.message, rule.param_name)
            except ValidationError:
                raise
            except Exception as exc:
                logger.error(
                    "[MW] 验证规则 '%s' 执行异常: %s",
                    rule.name,
                    exc,
                    exc_info=True,
                )
                raise ValidationError(
                    rule.name,
                    f"验证规则执行出错: {exc}",
                    rule.param_name,
                ) from exc

    def after(self, ctx: MiddlewareContext) -> None:
        pass  # no-op


# ---------------------------------------------------------------------------
# Performance monitoring middleware
# ---------------------------------------------------------------------------


class PerformanceMiddleware(Middleware):
    """性能监控中间件。

    记录函数执行耗时，超过阈值时发出警告。
    """

    def __init__(self, warn_threshold_ms: float = 1000.0) -> None:
        self._warn_threshold_ms = warn_threshold_ms

    def before(self, ctx: MiddlewareContext) -> None:
        ctx.metadata["perf_start"] = time.perf_counter()

    def after(self, ctx: MiddlewareContext) -> None:
        elapsed = ctx.elapsed_ms
        if elapsed > self._warn_threshold_ms:
            logger.warning(
                "[MW] 慢调用警告: %s 耗时 %.1fms (阈值 %.1fms)",
                ctx.func_name,
                elapsed,
                self._warn_threshold_ms,
            )


# ---------------------------------------------------------------------------
# Middleware chain
# ---------------------------------------------------------------------------


class MiddlewareChain:
    """中间件链 -- 按顺序执行 before / 包装函数 / after。

    可作为装饰器或直接调用 wrap。
    """

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> MiddlewareChain:
        """添加中间件到链尾，返回 self 以支持链式调用。"""
        self._middlewares.append(middleware)
        return self

    def remove(self, middleware: Middleware) -> None:
        """从链中移除中间件。"""
        self._middlewares.remove(middleware)

    def clear(self) -> None:
        """清空中间件链。"""
        self._middlewares.clear()

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """通过中间件链执行函数。

        Args:
            func: 要执行的函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            函数执行结果。
        """
        ctx = MiddlewareContext(
            func_name=getattr(func, "__qualname__", repr(func)),
            args=args,
            kwargs=kwargs,
        )

        # Before phase
        for mw in self._middlewares:
            try:
                mw.before(ctx)
            except Exception as exc:
                ctx.error = exc
                # Run after handlers that may want to handle the error
                for after_mw in self._middlewares:
                    try:
                        after_mw.after(ctx)
                    except Exception:
                        pass
                if ctx.error:
                    raise ctx.error from exc
                return ctx.result

        # Execute function
        start = time.perf_counter()
        try:
            ctx.result = func(*args, **kwargs)
        except Exception as exc:
            ctx.error = exc
        finally:
            ctx.elapsed_ms = (time.perf_counter() - start) * 1000

        # After phase (reverse order for proper unwinding)
        for mw in reversed(self._middlewares):
            try:
                mw.after(ctx)
            except Exception:
                logger.error("[MW] after 处理异常", exc_info=True)

        if ctx.error:
            raise ctx.error

        return ctx.result

    def wrap(self, func: F) -> F:
        """装饰器：将函数包装在中间件链中。

        Args:
            func: 要包装的函数。

        Returns:
            包装后的函数。
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(func, *args, **kwargs)

        return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Pre-built default chain
# ---------------------------------------------------------------------------


def create_default_chain() -> MiddlewareChain:
    """创建包含常用中间件的默认链。

    包含: LoggingMiddleware + PerformanceMiddleware + ErrorHandlingMiddleware。
    """
    chain = MiddlewareChain()
    chain.add(LoggingMiddleware(level=logging.DEBUG))
    chain.add(PerformanceMiddleware(warn_threshold_ms=2000.0))
    chain.add(ErrorHandlingMiddleware(swallow=True, default=None))
    return chain
