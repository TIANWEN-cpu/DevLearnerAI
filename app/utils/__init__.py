"""App utility modules.

Provides:
- error_handler: Centralized error classification and display
- events: Typed event bus for cross-widget communication
- middleware: Composable middleware chain (logging, validation, error handling)
- plugins: Plugin interface, discovery, and lifecycle management
- container: Dependency injection container with lazy resolution
- logger: Centralized structured logging configuration with performance tracking
- metrics: Simple in-memory metrics collector for key operations
"""

from app.utils.container import Container, Depends, get_container, inject, set_container
from app.utils.error_handler import ErrorCategory, classify_error, log_error, safe_operation
from app.utils.events import Event, EventBus, event_bus
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
from app.utils.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareChain,
    PerformanceMiddleware,
    ValidationMiddleware,
)
from app.utils.plugins import Plugin, PluginManager, discover_plugins

__all__ = [
    # Container
    "Container",
    "Depends",
    "get_container",
    "inject",
    "set_container",
    # Error handler
    "ErrorCategory",
    "classify_error",
    "log_error",
    "safe_operation",
    # Events
    "EventBus",
    "Event",
    "event_bus",
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
    # Middleware
    "ErrorHandlingMiddleware",
    "LoggingMiddleware",
    "MiddlewareChain",
    "PerformanceMiddleware",
    "ValidationMiddleware",
    # Plugins
    "Plugin",
    "PluginManager",
    "discover_plugins",
]
