"""App utility modules.

Provides:
- error_handler: Centralized error classification and display
- logger: Centralized structured logging configuration with performance tracking
- metrics: Simple in-memory metrics collector for key operations
- analytics: Local analytics collection (privacy-first)
"""

from app.utils.error_handler import ErrorCategory, classify_error, log_error, safe_operation
from app.utils.logger import (
    PerformanceTimer,
    SlowOperationTracker,
    StartupBreakdown,
    configure_logging,
    get_logger,
    slow_ops,
    startup_breakdown,
    track_operation,
)
from app.utils.metrics import MetricsCollector, get_metrics

__all__ = [
    # Error handler
    "ErrorCategory",
    "classify_error",
    "log_error",
    "safe_operation",
    # Logger
    "PerformanceTimer",
    "SlowOperationTracker",
    "StartupBreakdown",
    "configure_logging",
    "get_logger",
    "slow_ops",
    "startup_breakdown",
    "track_operation",
    # Metrics
    "MetricsCollector",
    "get_metrics",
]
