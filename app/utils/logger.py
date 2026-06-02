"""Centralized structured logging configuration.

Provides:
- StructuredJsonFormatter: JSON log output for machine parsing
- ContextFormatter: Human-readable log with extra context fields
- PerformanceTimer: Context manager that logs elapsed time for any operation
- SlowOperationTracker: Alerts when operations exceed a threshold
- configure_logging(): One-call setup for all log handlers (console, file, category files)
- get_logger(): Convenience wrapper returning a logger with category context
- MemoryUsageTracker: Periodic memory RSS logging
- StartupBreakdown: Phase-by-phase startup timing collector
"""

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

SLOW_OP_THRESHOLD_MS = 1000  # operations slower than this are flagged
MEMORY_CHECK_INTERVAL_SEC = 60  # periodic memory check interval

# ── Category log file mapping ─────────────────────────────────────────────────

_CATEGORY_FILES: dict[str, str] = {
    "ai": "ai.log",
    "db": "db.log",
    "practice": "practice.log",
}

# Module-name prefix -> category log file
_MODULE_CATEGORY_MAP: dict[str, str] = {
    "app.ai": "ai",
    "app.": "db",  # database module
}


def _detect_category(logger_name: str) -> Optional[str]:
    """Detect log category from logger module name."""
    if logger_name.startswith("app.ai"):
        return "ai"
    if logger_name in ("app.database", "app.db"):
        return "db"
    if logger_name.startswith("app.practice") or logger_name in ("app.practice_service",):
        return "practice"
    return None


# ── Formatters ────────────────────────────────────────────────────────────────


class StructuredJsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields:
        ts: ISO-8601 timestamp
        level: log level name
        logger: logger name
        msg: formatted message
        func: function name (if available)
        line: line number (if available)
        extra: any extra fields attached to the record
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.funcName and record.funcName != "<module>":
            log_entry["func"] = record.funcName
        if record.lineno and record.lineno > 0:
            log_entry["line"] = record.lineno

        # Attach extra fields (skip internal LogRecord attributes)
        _internal_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in _internal_attrs and k not in ("message", "asctime")
        }
        if extra_fields:
            # Filter non-serializable values
            safe_extra = {}
            for k, v in extra_fields.items():
                try:
                    json.dumps(v)
                    safe_extra[k] = v
                except (TypeError, ValueError):
                    safe_extra[k] = str(v)
            if safe_extra:
                log_entry["extra"] = safe_extra

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exc"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ContextFormatter(logging.Formatter):
    """Human-readable formatter with context fields.

    Format: ``2025-01-01 12:00:00 [name] LEVEL (func:line): message``
    Extra context fields are appended as ``key=value`` pairs.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = self.formatTime(record, self.datefmt)
        loc = ""
        if record.funcName and record.funcName != "<module>":
            loc = f" ({record.funcName}:{record.lineno})"

        msg = record.getMessage()
        level = record.levelname

        # Append extra context
        _internal_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in _internal_attrs and k not in ("message", "asctime")
        }
        extra_str = ""
        if extra_fields:
            parts = [f"{k}={v}" for k, v in extra_fields.items()]
            extra_str = " | " + " ".join(parts)

        line = f"{base} [{record.name}] {level}{loc}: {msg}{extra_str}"

        if record.exc_info and record.exc_info[0] is not None:
            line += "\n" + self.formatException(record.exc_info)
        return line


# ── Performance timer ─────────────────────────────────────────────────────────


class PerformanceTimer:
    """Context manager that measures and logs elapsed time.

    Usage::

        with PerformanceTimer("load_lessons", logger) as timer:
            ...
        # timer.elapsed_ms is available after exit

    If the operation exceeds *slow_threshold_ms*, it is logged at WARNING level;
    otherwise at DEBUG.
    """

    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
        slow_threshold_ms: float = SLOW_OP_THRESHOLD_MS,
        extra: Optional[dict[str, Any]] = None,
    ):
        self.operation = operation
        self.logger = logger or logging.getLogger("perf")
        self.slow_threshold_ms = slow_threshold_ms
        self.extra = extra or {}
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "PerformanceTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
        level = logging.WARNING if self.elapsed_ms > self.slow_threshold_ms else logging.DEBUG
        status = "error" if exc_type else "ok"
        self.logger.log(
            level,
            "%s completed in %.1f ms [%s]",
            self.operation,
            self.elapsed_ms,
            status,
            extra={**self.extra, "duration_ms": round(self.elapsed_ms, 1), "op": self.operation},
        )


@contextmanager
def track_operation(
    operation: str,
    logger: Optional[logging.Logger] = None,
    slow_threshold_ms: float = SLOW_OP_THRESHOLD_MS,
    extra: Optional[dict[str, Any]] = None,
):
    """Convenience context manager that returns a PerformanceTimer.

    Yields the timer so the caller can read ``timer.elapsed_ms``.
    """
    timer = PerformanceTimer(operation, logger, slow_threshold_ms, extra)
    with timer:
        yield timer


# ── Slow operation tracker ────────────────────────────────────────────────────


class SlowOperationTracker:
    """Collects and reports slow operations.

    Thread-safe. Keeps a bounded list of recent slow ops and exposes
    summary statistics.
    """

    def __init__(self, threshold_ms: float = SLOW_OP_THRESHOLD_MS, max_entries: int = 200):
        self.threshold_ms = threshold_ms
        self.max_entries = max_entries
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, operation: str, elapsed_ms: float, extra: Optional[dict[str, Any]] = None) -> None:
        """Record a slow operation if it exceeds the threshold."""
        if elapsed_ms < self.threshold_ms:
            return
        entry = {
            "op": operation,
            "ms": round(elapsed_ms, 1),
            "ts": time.time(),
            **(extra or {}),
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries :]

    def get_slow_ops(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent slow operations."""
        with self._lock:
            return list(self._entries[-limit:])

    def summary(self) -> dict[str, Any]:
        """Return aggregate slow-op statistics."""
        with self._lock:
            if not self._entries:
                return {"count": 0}
            durations = [e["ms"] for e in self._entries]
            return {
                "count": len(self._entries),
                "avg_ms": round(sum(durations) / len(durations), 1),
                "max_ms": round(max(durations), 1),
                "min_ms": round(min(durations), 1),
                "operations": list({e["op"] for e in self._entries}),
            }


# Global slow-op tracker instance
slow_ops = SlowOperationTracker()


# ── Startup breakdown ─────────────────────────────────────────────────────────


class StartupBreakdown:
    """Records phase-by-phase startup timing.

    Usage::

        startup = StartupBreakdown()
        startup.begin("db_init")
        ...  # do work
        startup.end("db_init")
        startup.report()  # logs summary
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("startup")
        self._phases: dict[str, float] = {}
        self._order: list[str] = []
        self._start_time = time.perf_counter()

    def begin(self, phase: str) -> None:
        """Mark the start of a named phase."""
        self._phases[f"{phase}_start"] = time.perf_counter()
        if phase not in self._order:
            self._order.append(phase)

    def end(self, phase: str) -> float:
        """Mark the end of a named phase. Returns elapsed ms."""
        start_key = f"{phase}_start"
        start = self._phases.get(start_key)
        if start is None:
            self.logger.warning("StartupBreakdown.end called for unknown phase: %s", phase)
            return 0.0
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._phases[phase] = elapsed_ms
        self.logger.info("Startup phase [%s]: %.1f ms", phase, elapsed_ms)
        return elapsed_ms

    def report(self) -> None:
        """Log a summary of all startup phases."""
        total_ms = (time.perf_counter() - self._start_time) * 1000
        lines = ["Startup breakdown:"]
        for phase in self._order:
            ms = self._phases.get(phase, 0.0)
            lines.append(f"  {phase}: {ms:.1f} ms")
        lines.append(f"  TOTAL: {total_ms:.1f} ms")
        self.logger.info("\n".join(lines))

    def get_phases(self) -> dict[str, float]:
        """Return a copy of all phase durations in ms."""
        return {phase: self._phases.get(phase, 0.0) for phase in self._order}


# Global startup breakdown instance
startup_breakdown = StartupBreakdown()


# ── Memory usage tracker ──────────────────────────────────────────────────────


class MemoryUsageTracker:
    """Periodically logs process RSS memory usage.

    Starts a daemon thread that checks memory at a fixed interval.
    Logs at WARNING level when above the high-water mark.
    """

    def __init__(
        self,
        interval_sec: float = MEMORY_CHECK_INTERVAL_SEC,
        high_water_mb: float = 300.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.interval_sec = interval_sec
        self.high_water_mb = high_water_mb
        self.logger = logger or logging.getLogger("memory")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _get_rss_mb(self) -> float:
        """Get current RSS in MB. Returns 0 if unavailable."""
        try:
            import psutil

            return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        except ImportError:
            pass
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            maxrss = usage.ru_maxrss
            if hasattr(os, "uname") and os.uname().sysname == "Darwin":
                maxrss /= 1024 * 1024
            else:
                maxrss /= 1024
            return float(maxrss)
        except (ImportError, AttributeError):
            return 0.0

    def _monitor_loop(self) -> None:
        while not self._stop_event.wait(self.interval_sec):
            rss = self._get_rss_mb()
            if rss <= 0:
                continue
            if rss > self.high_water_mb:
                self.logger.warning(
                    "Memory high-water mark exceeded: %.1f MB (threshold: %.1f MB)", rss, self.high_water_mb
                )
            else:
                self.logger.debug("Memory usage: %.1f MB", rss)

    def start(self) -> None:
        """Start the background memory monitoring thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name="memory-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background monitoring thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)


# ── Logging configuration ─────────────────────────────────────────────────────

_configured = False


def _create_rotating_handler(
    log_file: Path,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    encoding: str = "utf-8",
) -> RotatingFileHandler:
    """Create a rotating file handler with consistent configuration."""
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
    )
    return handler


def configure_logging(
    log_dir: Path,
    level: int = logging.INFO,
    json_format: bool = False,
    enable_category_files: bool = True,
    enable_slow_op_tracking: bool = True,
    enable_memory_tracking: bool = False,
    memory_interval_sec: float = MEMORY_CHECK_INTERVAL_SEC,
    memory_high_water_mb: float = 300.0,
) -> None:
    """Configure the application-wide logging system.

    Sets up:
    - Root logger with console + rotating file handler
    - Optional JSON formatting
    - Category-specific log files (ai, db, practice) if enabled
    - Slow operation tracking hook
    - Optional memory usage tracking thread

    Args:
        log_dir: Directory for log files.
        level: Root log level.
        json_format: If True, use JSON lines format for file output.
        enable_category_files: If True, route category logs to separate files.
        enable_slow_op_tracking: If True, install a filter that records slow ops.
        enable_memory_tracking: If True, start periodic memory usage logging.
        memory_interval_sec: Interval for memory checks.
        memory_high_water_mb: RSS threshold for memory warnings.
    """
    global _configured
    if _configured:
        return
    _configured = True

    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # ── Choose formatters ─────────────────────────────────────────────────────
    if json_format:
        file_formatter: logging.Formatter = StructuredJsonFormatter()
    else:
        file_formatter = ContextFormatter(
            fmt="%(asctime)s [%(name)s] %(levelname)s%(context)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    console_formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Main app log file ─────────────────────────────────────────────────────
    app_handler = _create_rotating_handler(log_dir / "app.log")
    app_handler.setFormatter(file_formatter)
    root.addHandler(app_handler)

    # ── Console handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root.addHandler(console_handler)

    # ── Category log files ────────────────────────────────────────────────────
    if enable_category_files:
        _category_handlers: dict[str, logging.Handler] = {}
        for category, filename in _CATEGORY_FILES.items():
            handler = _create_rotating_handler(log_dir / filename)
            handler.setFormatter(file_formatter)
            handler.setLevel(logging.DEBUG)
            _category_handlers[category] = handler

        # Attach a filter to each category handler that only passes matching loggers
        for category, handler in _category_handlers.items():
            cat_filter = _CategoryFilter(category)
            handler.addFilter(cat_filter)
            root.addHandler(handler)

    # ── Slow-op filter ────────────────────────────────────────────────────────
    if enable_slow_op_tracking:
        root.addFilter(_SlowOpFilter())

    # ── Memory tracker ────────────────────────────────────────────────────────
    if enable_memory_tracking:
        tracker = MemoryUsageTracker(
            interval_sec=memory_interval_sec,
            high_water_mb=memory_high_water_mb,
        )
        tracker.start()


class _CategoryFilter(logging.Filter):
    """Filter that only passes records from loggers matching a category."""

    def __init__(self, category: str):
        super().__init__()
        self.category = category

    def filter(self, record: logging.LogRecord) -> bool:
        detected = _detect_category(record.name)
        return detected == self.category


class _SlowOpFilter(logging.Filter):
    """Filter that records slow operations into the global tracker.

    This is a no-op filter (always passes) -- it piggybacks on
    PerformanceTimer records to update the global SlowOperationTracker.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Check if this record has performance data
        duration_ms = getattr(record, "duration_ms", None)
        op = getattr(record, "op", None)
        if duration_ms is not None and op is not None:
            slow_ops.record(op, duration_ms)
        return True


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name.

    This is a thin convenience wrapper around ``logging.getLogger``.
    Use module-level names (e.g. ``__name__``) for automatic category routing.
    """
    return logging.getLogger(name)
