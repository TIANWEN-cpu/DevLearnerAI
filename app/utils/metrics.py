"""Simple in-memory metrics collector for key application operations.

Provides:
- MetricsCollector: Central metrics registry with counters, timers, and gauges
- API call success/failure tracking
- Exercise completion rate tracking
- Operation timing histograms
- Periodic metrics logging

Thread-safe. All data is in-memory (no persistence) -- suitable for
diagnostics during a single application session.
"""

import logging
import threading
import time
from collections import defaultdict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Counter:
    """A simple thread-safe counter with labels."""

    def __init__(self, name: str):
        self.name = name
        self._values: dict[str, int] = defaultdict(int)
        self._total = 0
        self._lock = threading.Lock()

    def inc(self, label: str = "default", amount: int = 1) -> None:
        with self._lock:
            self._values[label] += amount
            self._total += amount

    def get(self, label: str = "default") -> int:
        with self._lock:
            return self._values[label]

    def total(self) -> int:
        with self._lock:
            return self._total

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"name": self.name, "total": self._total, "by_label": dict(self._values)}


class Timer:
    """Tracks duration statistics for operations (thread-safe)."""

    def __init__(self, name: str, max_samples: int = 500):
        self.name = name
        self.max_samples = max_samples
        self._samples: list[float] = []
        self._count = 0
        self._total_ms = 0.0
        self._lock = threading.Lock()

    def record(self, elapsed_ms: float) -> None:
        with self._lock:
            self._count += 1
            self._total_ms += elapsed_ms
            self._samples.append(elapsed_ms)
            if len(self._samples) > self.max_samples:
                self._samples = self._samples[-self.max_samples:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if not self._samples:
                return {"name": self.name, "count": 0}
            sorted_s = sorted(self._samples)
            return {
                "name": self.name,
                "count": self._count,
                "avg_ms": round(self._total_ms / self._count, 1),
                "p50_ms": round(sorted_s[len(sorted_s) // 2], 1),
                "p95_ms": round(sorted_s[int(len(sorted_s) * 0.95)], 1),
                "p99_ms": round(sorted_s[int(len(sorted_s) * 0.99)], 1),
                "max_ms": round(max(sorted_s), 1),
                "min_ms": round(min(sorted_s), 1),
            }


class Gauge:
    """A point-in-time value gauge (thread-safe)."""

    def __init__(self, name: str):
        self.name = name
        self._value: float = 0.0
        self._lock = threading.Lock()

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def get(self) -> float:
        with self._lock:
            return self._value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"name": self.name, "value": self._value}


class MetricsCollector:
    """Central metrics registry.

    Provides convenience methods for common application metrics:
    - API calls (success/failure with latency)
    - Exercise attempts (pass/fail/score)
    - Database operations (latency)
    - Code execution (latency, exit codes)
    - Content loading (latency)
    """

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._timers: dict[str, Timer] = {}
        self._gauges: dict[str, Gauge] = {}
        self._lock = threading.Lock()

    # ── Counter helpers ───────────────────────────────────────────────────────

    def _get_counter(self, name: str) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name)
            return self._counters[name]

    def _get_timer(self, name: str) -> Timer:
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer(name)
            return self._timers[name]

    def _get_gauge(self, name: str) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name)
            return self._gauges[name]

    # ── API call metrics ──────────────────────────────────────────────────────

    def record_api_call(self, model: str, success: bool, elapsed_ms: float, tokens: int = 0) -> None:
        """Record an AI API call with outcome and latency."""
        status = "success" if success else "failure"
        self._get_counter("api_calls").inc(status)
        self._get_counter(f"api_calls_by_model.{model}").inc(status)
        self._get_timer("api_latency").record(elapsed_ms)
        if tokens > 0:
            self._get_counter("api_tokens").inc("total", tokens)
        logger.debug(
            "API call recorded: model=%s status=%s latency=%.1fms tokens=%d",
            model, status, elapsed_ms, tokens,
        )

    def get_api_summary(self) -> dict[str, Any]:
        """Return a summary of API call metrics."""
        counter = self._get_counter("api_calls")
        timer = self._get_timer("api_latency")
        tokens = self._get_counter("api_tokens")
        success = counter.get("success")
        failure = counter.get("failure")
        total = success + failure
        return {
            "total_calls": total,
            "success": success,
            "failure": failure,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0.0,
            "latency": timer.snapshot(),
            "total_tokens": tokens.total(),
        }

    # ── Exercise metrics ──────────────────────────────────────────────────────

    def record_exercise_attempt(self, exercise_id: str, passed: bool, score: int, elapsed_ms: float) -> None:
        """Record an exercise evaluation attempt."""
        status = "passed" if passed else "failed"
        self._get_counter("exercise_attempts").inc(status)
        self._get_timer("exercise_eval_latency").record(elapsed_ms)
        self._get_counter("exercise_scores").inc(str(score // 10 * 10))  # bucketed by 10s
        logger.debug(
            "Exercise attempt: id=%s status=%s score=%d latency=%.1fms",
            exercise_id, status, score, elapsed_ms,
        )

    def get_exercise_summary(self) -> dict[str, Any]:
        """Return a summary of exercise attempt metrics."""
        counter = self._get_counter("exercise_attempts")
        timer = self._get_timer("exercise_eval_latency")
        passed = counter.get("passed")
        failed = counter.get("failed")
        total = passed + failed
        return {
            "total_attempts": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
            "latency": timer.snapshot(),
            "score_distribution": dict(self._get_counter("exercise_scores").snapshot().get("by_label", {})),
        }

    # ── Database metrics ──────────────────────────────────────────────────────

    def record_db_operation(self, operation: str, elapsed_ms: float, success: bool = True) -> None:
        """Record a database operation."""
        status = "success" if success else "error"
        self._get_counter("db_operations").inc(status)
        self._get_timer("db_latency").record(elapsed_ms)
        self._get_counter(f"db_op.{operation}").inc()
        if elapsed_ms > 500:
            logger.warning("Slow DB operation: %s took %.1f ms", operation, elapsed_ms)

    def get_db_summary(self) -> dict[str, Any]:
        """Return a summary of database metrics."""
        counter = self._get_counter("db_operations")
        timer = self._get_timer("db_latency")
        return {
            "total_operations": counter.total(),
            "success": counter.get("success"),
            "errors": counter.get("error"),
            "latency": timer.snapshot(),
        }

    # ── Code execution metrics ────────────────────────────────────────────────

    def record_code_execution(self, success: bool, exit_code: int, elapsed_ms: float) -> None:
        """Record a code execution result."""
        status = "success" if success else "failure"
        self._get_counter("code_executions").inc(status)
        self._get_timer("code_exec_latency").record(elapsed_ms)
        self._get_counter("code_exit_codes").inc(str(exit_code))
        logger.debug(
            "Code execution: status=%s exit_code=%d latency=%.1fms",
            status, exit_code, elapsed_ms,
        )

    def get_code_exec_summary(self) -> dict[str, Any]:
        """Return code execution metrics."""
        counter = self._get_counter("code_executions")
        timer = self._get_timer("code_exec_latency")
        success = counter.get("success")
        failure = counter.get("failure")
        total = success + failure
        return {
            "total_executions": total,
            "success": success,
            "failure": failure,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0.0,
            "latency": timer.snapshot(),
        }

    # ── Content loading metrics ───────────────────────────────────────────────

    def record_content_load(self, content_type: str, elapsed_ms: float, cache_hit: bool = False) -> None:
        """Record a content loading operation."""
        self._get_counter("content_loads").inc("hit" if cache_hit else "miss")
        self._get_timer("content_load_latency").record(elapsed_ms)
        self._get_counter(f"content_loads_by_type.{content_type}").inc()

    def get_content_summary(self) -> dict[str, Any]:
        """Return content loading metrics."""
        counter = self._get_counter("content_loads")
        timer = self._get_timer("content_load_latency")
        return {
            "total_loads": counter.total(),
            "cache_hits": counter.get("hit"),
            "cache_misses": counter.get("miss"),
            "latency": timer.snapshot(),
        }

    # ── General operations ────────────────────────────────────────────────────

    def record_operation(self, name: str, elapsed_ms: float, success: bool = True) -> None:
        """Record a generic operation timing."""
        self._get_timer(f"op.{name}").record(elapsed_ms)
        self._get_counter(f"op_count.{name}").inc("success" if success else "failure")

    # ── Full report ───────────────────────────────────────────────────────────

    def full_report(self) -> dict[str, Any]:
        """Return a complete metrics snapshot."""
        return {
            "api": self.get_api_summary(),
            "exercises": self.get_exercise_summary(),
            "database": self.get_db_summary(),
            "code_execution": self.get_code_exec_summary(),
            "content": self.get_content_summary(),
        }

    def log_summary(self) -> None:
        """Log a human-readable summary of all metrics at INFO level."""
        report = self.full_report()
        lines = ["=== Metrics Summary ==="]
        for section, data in report.items():
            lines.append(f"  [{section}]")
            for key, value in data.items():
                lines.append(f"    {key}: {value}")
        logger.info("\n".join(lines))


# ── Global singleton ──────────────────────────────────────────────────────────

_metrics: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Return the global MetricsCollector singleton (thread-safe)."""
    global _metrics
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:
                _metrics = MetricsCollector()
    return _metrics
