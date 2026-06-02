"""事件系统模块 -- 跨组件通信基础设施。

提供类型安全的事件总线，用于解耦 widget 之间的直接调用。
所有事件通过 EventBus 单例发布和订阅，发送者无需知道接收者。

使用示例::

    from app.utils.events import event_bus, LessonCompletedEvent

    # 订阅
    def on_lesson_done(event: LessonCompletedEvent):
        logger.info("课程 %s 已完成", event.lesson_id)

    event_bus.subscribe(LessonCompletedEvent, on_lesson_done)

    # 发布
    event_bus.publish(LessonCompletedEvent(lesson_id="py-01", track_id="python"))

    # 退订
    event_bus.unsubscribe(LessonCompletedEvent, on_lesson_done)
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Event")


# ---------------------------------------------------------------------------
# Base event class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """所有事件的基类。

    每个事件子类应定义为 frozen dataclass，包含该事件的类型化载荷字段。
    timestamp 在发布时自动设置。

    Attributes:
        timestamp: 事件创建时间戳（自动填充）。
    """

    timestamp: datetime = field(default_factory=datetime.now, init=False)

    @classmethod
    def event_name(cls) -> str:
        """返回事件的可读名称，用于日志和调试。"""
        return cls.__name__


# ---------------------------------------------------------------------------
# Domain events -- Learning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LessonOpenedEvent(Event):
    """课程被打开。"""

    lesson_id: str = ""
    track_id: str = ""


@dataclass(frozen=True)
class LessonCompletedEvent(Event):
    """课程被标记为完成。"""

    lesson_id: str = ""
    track_id: str = ""


@dataclass(frozen=True)
class LessonNoteSavedEvent(Event):
    """课程笔记已保存。"""

    lesson_id: str = ""
    has_content: bool = False


# ---------------------------------------------------------------------------
# Domain events -- Practice
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExerciseAttemptRecordedEvent(Event):
    """练习评测结果已记录。"""

    exercise_id: str = ""
    score: int = 0
    passed: bool = False
    duration_sec: int = 0


@dataclass(frozen=True)
class ExerciseDraftSavedEvent(Event):
    """练习草稿已自动保存。"""

    exercise_id: str = ""


@dataclass(frozen=True)
class ExerciseDraftClearedEvent(Event):
    """练习草稿已清除。"""

    exercise_id: str = ""


@dataclass(frozen=True)
class ReviewCompletedEvent(Event):
    """间隔复习已完成。"""

    exercise_id: str = ""
    quality: int = 0


# ---------------------------------------------------------------------------
# Domain events -- AI Mentor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MentorSessionCreatedEvent(Event):
    """AI 会话已创建。"""

    session_id: int = 0
    session_name: str = ""


@dataclass(frozen=True)
class MentorSessionDeletedEvent(Event):
    """AI 会话已删除。"""

    session_id: int = 0


@dataclass(frozen=True)
class MentorSessionSwitchedEvent(Event):
    """AI 会话已切换。"""

    session_id: int = 0


@dataclass(frozen=True)
class MentorMessageSentEvent(Event):
    """消息已发送到 AI 会话。"""

    session_id: int = 0
    role: str = ""


# ---------------------------------------------------------------------------
# Domain events -- Bookmarks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookmarkAddedEvent(Event):
    """书签已添加。"""

    item_type: str = ""
    item_id: str = ""
    title: str = ""


@dataclass(frozen=True)
class BookmarkRemovedEvent(Event):
    """书签已移除。"""

    item_type: str = ""
    item_id: str = ""


# ---------------------------------------------------------------------------
# Domain events -- Achievements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AchievementUnlockedEvent(Event):
    """成就已解锁。"""

    achievement_id: str = ""
    title: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Domain events -- Knowledge Files
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeFileAddedEvent(Event):
    """知识库文件已添加。"""

    display_name: str = ""
    file_path: str = ""


@dataclass(frozen=True)
class KnowledgeFileRemovedEvent(Event):
    """知识库文件已移除。"""

    file_id: int = 0


# ---------------------------------------------------------------------------
# Domain events -- Application
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataResetEvent(Event):
    """学习数据已重置。"""


@dataclass(frozen=True)
class DataImportedEvent(Event):
    """学习数据已导入。"""

    record_count: int = 0


@dataclass(frozen=True)
class DataExportedEvent(Event):
    """学习数据已导出。"""

    format: str = ""


@dataclass(frozen=True)
class ThemeChangedEvent(Event):
    """主题已切换。"""

    dark_mode: bool = False


@dataclass(frozen=True)
class FontSizeChangedEvent(Event):
    """字体大小已更改。"""

    font_size: str = "medium"


@dataclass(frozen=True)
class NavigationEvent(Event):
    """导航到指定页面。"""

    page_name: str = ""


@dataclass(frozen=True)
class AppErrorEvent(Event):
    """应用级错误。"""

    category: str = ""
    message: str = ""
    context: str = ""


# ---------------------------------------------------------------------------
# EventBus -- publish / subscribe
# ---------------------------------------------------------------------------


Handler = Callable[[Any], None]


class EventBus:
    """线程安全的事件总线。

    允许组件通过事件类型解耦通信。支持同步和异步（Qt 主线程）分发。
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[Event], list[Handler]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: Type[T], handler: Handler) -> None:
        """订阅指定类型的事件。

        Args:
            event_type: 事件类。
            handler: 回调函数，接受一个事件实例参数。
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
                logger.debug(
                    "事件订阅: %s -> %s",
                    event_type.event_name(),
                    getattr(handler, "__qualname__", repr(handler)),
                )

    def unsubscribe(self, event_type: Type[T], handler: Handler) -> None:
        """退订指定类型的事件。

        Args:
            event_type: 事件类。
            handler: 之前订阅的回调函数。
        """
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
                logger.debug(
                    "事件退订: %s -> %s",
                    event_type.event_name(),
                    getattr(handler, "__qualname__", repr(handler)),
                )

    def publish(self, event: Event) -> None:
        """发布事件，同步调用所有订阅者。

        Args:
            event: 事件实例。
        """
        with self._lock:
            handlers = list(self._handlers.get(type(event), []))

        event_name = type(event).event_name()
        logger.debug("发布事件: %s (订阅者: %d)", event_name, len(handlers))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.error(
                    "事件处理异常: %s -> %s",
                    event_name,
                    getattr(handler, "__qualname__", repr(handler)),
                    exc_info=True,
                )

    def subscriber_count(self, event_type: Type[T]) -> int:
        """查询指定事件类型的订阅者数量。"""
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def clear(self, event_type: Optional[Type[T]] = None) -> None:
        """清除订阅。

        Args:
            event_type: 指定事件类型则仅清除该类型的订阅，
                        不指定则清除所有订阅。
        """
        with self._lock:
            if event_type:
                self._handlers.pop(event_type, None)
            else:
                self._handlers.clear()

    def handler_count(self) -> int:
        """返回所有事件类型的总订阅者数量。"""
        with self._lock:
            return sum(len(h) for h in self._handlers.values())

    def registered_event_types(self) -> list[Type[Event]]:
        """返回所有已注册事件类型。"""
        with self._lock:
            return list(self._handlers.keys())


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

event_bus = EventBus()
