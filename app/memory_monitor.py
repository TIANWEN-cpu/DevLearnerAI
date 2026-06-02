"""Lightweight memory monitoring for cache eviction decisions.

Tracks process RSS and provides a simple API for checking whether
caches should be trimmed. Uses psutil when available, falls back to
the resource module on Unix, or returns 0 on unsupported platforms.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

# Threshold in MB above which caches should be trimmed
_CACHE_TRIM_THRESHOLD_MB = 300
# Threshold in MB above which aggressive cleanup is triggered
_AGGRESSIVE_CLEANUP_THRESHOLD_MB = 500


def get_rss_mb() -> float:
    """Return current process RSS in MB.

    Uses psutil if available, falls back to resource module on Unix,
    or returns 0.0 on unsupported platforms.
    """
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass

    if sys.platform != "win32":
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            maxrss = usage.ru_maxrss
            if sys.platform == "darwin":
                maxrss /= 1024 * 1024
            else:
                maxrss /= 1024
            return maxrss
        except Exception:
            pass

    return 0.0


def should_trim_caches() -> bool:
    """Return True if memory usage suggests caches should be trimmed."""
    rss = get_rss_mb()
    return rss > _CACHE_TRIM_THRESHOLD_MB if rss > 0 else False


def should_aggressive_cleanup() -> bool:
    """Return True if memory usage is critically high."""
    rss = get_rss_mb()
    return rss > _AGGRESSIVE_CLEANUP_THRESHOLD_MB if rss > 0 else False


def log_memory_usage(label: str = "") -> None:
    """Log current memory usage at DEBUG level."""
    rss = get_rss_mb()
    if rss > 0:
        logger.debug("Memory [%s]: %.1f MB RSS", label or "check", rss)
