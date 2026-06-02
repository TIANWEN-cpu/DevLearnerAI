"""Lightweight memory monitoring for cache eviction decisions.

Tracks process RSS and provides a simple API for checking whether
caches should be trimmed. Uses psutil when available, falls back to
the resource module on Unix, ctypes on Windows, or returns 0 on
unsupported platforms.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

# Threshold in MB above which caches should be trimmed
_CACHE_TRIM_THRESHOLD_MB = 300
# Threshold in MB above which aggressive cleanup is triggered
_AGGRESSIVE_CLEANUP_THRESHOLD_MB = 500

# Windows memory info cache (avoid repeated syscalls within same interval)
_win_rss_cache: float = 0.0
_win_rss_cache_ts: float = 0.0
_WIN_RSS_CACHE_TTL: float = 2.0  # seconds


def _get_rss_windows() -> float:
    """Return current process RSS on Windows using ctypes/kernel32."""
    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        psapi = ctypes.windll.psapi  # type: ignore[attr-defined]

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = kernel32.GetCurrentProcess()
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        logger.debug("通过 Win32 API 获取进程内存失败", exc_info=True)
    return 0.0


def get_rss_mb() -> float:
    """Return current process RSS in MB.

    Uses psutil if available, falls back to ctypes on Windows,
    resource module on Unix, or returns 0.0 on unsupported platforms.
    Results are cached for 2 seconds to avoid repeated syscalls.
    """
    import time

    global _win_rss_cache, _win_rss_cache_ts

    now = time.monotonic()
    if _win_rss_cache > 0 and (now - _win_rss_cache_ts) < _WIN_RSS_CACHE_TTL:
        return _win_rss_cache

    try:
        import psutil

        rss = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        _win_rss_cache = rss
        _win_rss_cache_ts = now
        return rss
    except ImportError:
        pass

    if sys.platform == "win32":
        rss = _get_rss_windows()
        _win_rss_cache = rss
        _win_rss_cache_ts = now
        return rss

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
            logger.debug("通过 resource 模块获取 RSS 失败", exc_info=True)

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
