"""集中式错误处理模块。

提供错误分类、用户友好消息映射、日志集成和统一的错误处理模式。

错误分类:
- DatabaseError: 数据库操作相关
- NetworkError: 网络/API 通信相关
- FileIOError: 文件读写相关
- AuthError: 认证/凭证相关
- ValidationError: 输入验证相关
- SandboxError: 代码沙箱执行相关
- UIError: 界面操作相关
"""

import logging
import sqlite3
import urllib.error
from collections.abc import Callable
from enum import Enum
from typing import Optional

from PyQt5.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class ErrorCategory(Enum):
    """错误分类枚举。"""

    DATABASE = "database"
    NETWORK = "network"
    FILE_IO = "file_io"
    AUTH = "auth"
    VALIDATION = "validation"
    SANDBOX = "sandbox"
    UI = "ui"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# User-friendly message mapping
# ---------------------------------------------------------------------------

_USER_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.DATABASE: "数据读写出现问题，请稍后重试。如果问题持续，可以尝试重启应用。",
    ErrorCategory.NETWORK: "网络连接失败，请检查网络设置和 API 地址是否正确。",
    ErrorCategory.FILE_IO: "文件读写失败，请检查文件是否存在且有读写权限。",
    ErrorCategory.AUTH: "认证失败，请检查 API 密钥是否正确或是否已过期。",
    ErrorCategory.VALIDATION: "输入内容不符合要求，请检查后重试。",
    ErrorCategory.SANDBOX: "代码执行出现问题，请检查代码后重试。",
    ErrorCategory.UI: "界面操作失败，请稍后重试。",
    ErrorCategory.UNKNOWN: "发生未知错误，请稍后重试。",
}

# Maps specific exception types to categories
_EXCEPTION_CATEGORY_MAP: dict[type, ErrorCategory] = {
    sqlite3.Error: ErrorCategory.DATABASE,
    sqlite3.OperationalError: ErrorCategory.DATABASE,
    sqlite3.IntegrityError: ErrorCategory.DATABASE,
    OSError: ErrorCategory.FILE_IO,
    IOError: ErrorCategory.FILE_IO,
    FileNotFoundError: ErrorCategory.FILE_IO,
    PermissionError: ErrorCategory.FILE_IO,
    ConnectionError: ErrorCategory.NETWORK,
    TimeoutError: ErrorCategory.NETWORK,
    urllib.error.URLError: ErrorCategory.NETWORK,
    urllib.error.HTTPError: ErrorCategory.NETWORK,
    ValueError: ErrorCategory.VALIDATION,
    KeyError: ErrorCategory.VALIDATION,
    TypeError: ErrorCategory.VALIDATION,
}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def classify_error(exc: Exception) -> ErrorCategory:
    """根据异常类型分类错误。

    Args:
        exc: 异常实例。

    Returns:
        ErrorCategory 分类结果。
    """
    # Check specific HTTP auth errors
    if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403):
        return ErrorCategory.AUTH

    for exc_type, category in _EXCEPTION_CATEGORY_MAP.items():
        if isinstance(exc, exc_type):
            return category

    return ErrorCategory.UNKNOWN


def get_user_message(exc: Exception, context: str = "") -> str:
    """获取用户友好的错误消息。

    Args:
        exc: 异常实例。
        context: 额外上下文描述（可选）。

    Returns:
        用户友好的错误消息字符串。
    """
    category = classify_error(exc)
    base_msg = _USER_MESSAGES[category]

    # Add context hint if provided
    if context:
        return f"{context}：{base_msg}"
    return base_msg


def get_http_error_message(exc: urllib.error.HTTPError) -> str:
    """获取 HTTP 错误的用户友好消息。

    Args:
        exc: HTTP 错误异常。

    Returns:
        用户友好的错误消息字符串。
    """
    status_messages = {
        400: "请求格式有误，请检查设置后重试。",
        401: "API 密钥无效或已过期，请到 AI 设置里更新密钥。",
        403: "没有访问权限，请确认 API 密钥权限是否足够。",
        404: "API 地址不存在，请检查 Host 地址是否正确。",
        429: "请求过于频繁，请稍等片刻后重试。",
        500: "服务器内部错误，请稍后重试。",
        502: "服务网关异常，请稍后重试。",
        503: "服务暂时不可用，请稍后重试。",
    }
    return status_messages.get(
        exc.code,
        f"AI 服务请求失败（HTTP {exc.code}），请检查设置或稍后重试。",
    )


def log_error(
    exc: Exception,
    context: str = "",
    level: int = logging.ERROR,
    include_traceback: bool = True,
) -> ErrorCategory:
    """记录错误到日志并返回错误分类。

    Args:
        exc: 异常实例。
        context: 错误发生的上下文描述。
        level: 日志级别。
        include_traceback: 是否包含完整回溯。

    Returns:
        ErrorCategory 分类结果。
    """
    category = classify_error(exc)
    prefix = f"[{category.value}]"
    message = f"{prefix} {context}: {exc}" if context else f"{prefix} {exc}"

    if include_traceback:
        logger.log(level, message, exc_info=True)
    else:
        logger.log(level, message)

    return category


# ---------------------------------------------------------------------------
# UI error display helpers
# ---------------------------------------------------------------------------


def show_error_dialog(
    parent: Optional[QWidget],
    exc: Exception,
    context: str = "",
    title: str = "操作失败",
    log: bool = True,
) -> None:
    """显示错误对话框（同时记录日志）。

    Args:
        parent: 父窗口组件。
        exc: 异常实例。
        context: 额外上下文描述。
        title: 对话框标题。
        log: 是否同时记录日志。
    """
    if log:
        log_error(exc, context)

    message = get_user_message(exc, context)
    QMessageBox.critical(parent, title, message)


def show_warning_dialog(
    parent: Optional[QWidget],
    message: str,
    title: str = "提示",
) -> None:
    """显示警告对话框。

    Args:
        parent: 父窗口组件。
        message: 警告消息。
        title: 对话框标题。
    """
    QMessageBox.warning(parent, title, message)


def show_info_dialog(
    parent: Optional[QWidget],
    message: str,
    title: str = "提示",
) -> None:
    """显示信息对话框。

    Args:
        parent: 父窗口组件。
        message: 信息消息。
        title: 对话框标题。
    """
    QMessageBox.information(parent, title, message)


# ---------------------------------------------------------------------------
# Decorator for safe operations
# ---------------------------------------------------------------------------


def safe_operation(
    context: str = "",
    default: object = None,
    log_level: int = logging.ERROR,
    reraise: bool = False,
) -> Callable[..., Callable[..., object]]:
    """装饰器：为函数添加统一的错误处理。

    Args:
        context: 操作上下文描述。
        default: 出错时返回的默认值。
        log_level: 日志级别。
        reraise: 是否重新抛出异常。

    Returns:
        装饰后的函数。
    """

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                log_error(exc, context or func.__qualname__, level=log_level)
                if reraise:
                    raise
                return default

        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
