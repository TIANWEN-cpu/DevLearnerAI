"""Tests for app.utils.middleware -- Middleware chain."""

import logging
from unittest.mock import patch

import pytest

from app.utils.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    PerformanceMiddleware,
    ValidationError,
    ValidationMiddleware,
    ValidationRule,
    create_default_chain,
)


class TestMiddlewareContext:
    """Test MiddlewareContext."""

    def test_basic_creation(self):
        ctx = MiddlewareContext("my_func", args=(1, 2), kwargs={"key": "val"})
        assert ctx.func_name == "my_func"
        assert ctx.args == (1, 2)
        assert ctx.kwargs == {"key": "val"}
        assert ctx.metadata == {}
        assert ctx.result is None
        assert ctx.error is None
        assert ctx.elapsed_ms == 0.0

    def test_defaults(self):
        ctx = MiddlewareContext("func")
        assert ctx.args == ()
        assert ctx.kwargs == {}


class TestLoggingMiddleware:
    """Test LoggingMiddleware."""

    def test_before_logs_call(self):
        mw = LoggingMiddleware(level=logging.DEBUG)
        ctx = MiddlewareContext("test_func")
        with patch("app.utils.middleware.logger") as mock_logger:
            mw.before(ctx)
            mock_logger.log.assert_called_once()

    def test_after_logs_success(self):
        mw = LoggingMiddleware()
        ctx = MiddlewareContext("test_func")
        ctx.elapsed_ms = 10.0
        with patch("app.utils.middleware.logger") as mock_logger:
            mw.after(ctx)
            mock_logger.log.assert_called_once()

    def test_after_logs_failure(self):
        mw = LoggingMiddleware()
        ctx = MiddlewareContext("test_func")
        ctx.elapsed_ms = 5.0
        ctx.error = RuntimeError("boom")
        with patch("app.utils.middleware.logger") as mock_logger:
            mw.after(ctx)
            mock_logger.warning.assert_called_once()

    def test_log_args(self):
        mw = LoggingMiddleware(log_args=True)
        ctx = MiddlewareContext("test_func", args=(1,), kwargs={"a": 2})
        with patch("app.utils.middleware.logger") as mock_logger:
            mw.before(ctx)
            mock_logger.log.assert_called_once()
            # Args should be in the log message
            call_args = mock_logger.log.call_args
            assert "args=" in str(call_args) or "kwargs=" in str(call_args)


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware."""

    def test_no_error_passes_through(self):
        mw = ErrorHandlingMiddleware()
        ctx = MiddlewareContext("func")
        ctx.result = 42
        mw.after(ctx)
        assert ctx.result == 42
        assert ctx.error is None

    def test_swallow_error(self):
        mw = ErrorHandlingMiddleware(swallow=True, default=-1)
        ctx = MiddlewareContext("func")
        ctx.error = RuntimeError("boom")
        mw.after(ctx)
        assert ctx.error is None
        assert ctx.result == -1

    def test_reraise_error(self):
        mw = ErrorHandlingMiddleware(reraise=True)
        ctx = MiddlewareContext("func")
        ctx.error = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            mw.after(ctx)

    def test_before_is_noop(self):
        mw = ErrorHandlingMiddleware()
        ctx = MiddlewareContext("func")
        mw.before(ctx)  # should not raise


class TestValidationMiddleware:
    """Test ValidationMiddleware."""

    def test_passes_when_all_rules_pass(self):
        rule = ValidationRule(
            name="non_empty",
            check=lambda lesson_id, **kw: bool(lesson_id),
            message="lesson_id required",
            param_name="lesson_id",
        )
        mw = ValidationMiddleware([rule])
        ctx = MiddlewareContext("save", args=("lesson-1",))
        mw.before(ctx)  # should not raise

    def test_fails_when_rule_fails(self):
        rule = ValidationRule(
            name="non_empty",
            check=lambda lesson_id, **kw: bool(lesson_id),
            message="lesson_id required",
            param_name="lesson_id",
        )
        mw = ValidationMiddleware([rule])
        ctx = MiddlewareContext("save", args=("",))
        with pytest.raises(ValidationError) as exc_info:
            mw.before(ctx)
        assert exc_info.value.rule_name == "non_empty"

    def test_after_is_noop(self):
        mw = ValidationMiddleware()
        ctx = MiddlewareContext("func")
        mw.after(ctx)  # should not raise

    def test_add_rule(self):
        mw = ValidationMiddleware()
        assert len(mw._rules) == 0
        mw.add_rule(ValidationRule("test", lambda: True, "fail"))
        assert len(mw._rules) == 1

    def test_rule_exception_wraps_in_validation_error(self):
        def bad_rule(*args, **kwargs):
            raise RuntimeError("internal error")

        rule = ValidationRule(name="bad", check=bad_rule, message="fail")
        mw = ValidationMiddleware([rule])
        ctx = MiddlewareContext("func")
        with pytest.raises(ValidationError) as exc_info:
            mw.before(ctx)
        assert "内部" in str(exc_info.value) or "出错" in str(exc_info.value) or "internal" in str(exc_info.value)


class TestPerformanceMiddleware:
    """Test PerformanceMiddleware."""

    def test_records_elapsed_time(self):
        mw = PerformanceMiddleware(warn_threshold_ms=100.0)
        ctx = MiddlewareContext("func")
        mw.before(ctx)
        assert "perf_start" in ctx.metadata

    def test_warns_on_slow_call(self):
        mw = PerformanceMiddleware(warn_threshold_ms=1.0)
        ctx = MiddlewareContext("func")
        ctx.elapsed_ms = 5000.0
        with patch("app.utils.middleware.logger") as mock_logger:
            mw.after(ctx)
            mock_logger.warning.assert_called_once()


class TestMiddlewareChain:
    """Test MiddlewareChain."""

    def test_add_and_remove(self):
        chain = MiddlewareChain()
        mw = LoggingMiddleware()
        chain.add(mw)
        assert len(chain._middlewares) == 1
        chain.remove(mw)
        assert len(chain._middlewares) == 0

    def test_clear(self):
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.add(ErrorHandlingMiddleware())
        chain.clear()
        assert len(chain._middlewares) == 0

    def test_execute_passes_through(self):
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.add(ErrorHandlingMiddleware(swallow=False))

        def add(a, b):
            return a + b

        result = chain.execute(add, 2, 3)
        assert result == 5

    def test_execute_with_error_swallowed(self):
        chain = MiddlewareChain()
        chain.add(ErrorHandlingMiddleware(swallow=True, default=-1))

        def fail():
            raise RuntimeError("boom")

        result = chain.execute(fail)
        assert result == -1

    def test_execute_with_error_reraised(self):
        chain = MiddlewareChain()
        chain.add(ErrorHandlingMiddleware(reraise=True))

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            chain.execute(fail)

    def test_wrap_decorator(self):
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())

        @chain.wrap
        def multiply(a, b):
            return a * b

        assert multiply(3, 4) == 12
        assert multiply.__name__ == "multiply"

    def test_before_blocks_execution(self):
        """If a middleware's before raises, the function should not execute."""
        call_count = [0]

        class BlockingMiddleware:
            def before(self, ctx):
                raise ValidationError("block", "blocked")

            def after(self, ctx):
                pass

        chain = MiddlewareChain()
        chain.add(BlockingMiddleware())
        chain.add(ErrorHandlingMiddleware(reraise=True))

        def should_not_run():
            call_count[0] += 1
            return 42

        with pytest.raises(ValidationError):
            chain.execute(should_not_run)
        assert call_count[0] == 0

    def test_chained_add(self):
        chain = MiddlewareChain()
        result = chain.add(LoggingMiddleware()).add(ErrorHandlingMiddleware())
        assert result is chain
        assert len(chain._middlewares) == 2


class TestCreateDefaultChain:
    """Test create_default_chain helper."""

    def test_creates_chain_with_three_middlewares(self):
        chain = create_default_chain()
        assert len(chain._middlewares) == 3

    def test_default_chain_wraps_function(self):
        chain = create_default_chain()

        def hello():
            return "world"

        wrapped = chain.wrap(hello)
        assert wrapped() == "world"
