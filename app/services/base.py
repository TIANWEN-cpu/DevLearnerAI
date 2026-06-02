"""服务基类 -- 所有服务的抽象基础。

定义服务接口契约和公共行为。
"""

from __future__ import annotations

import logging

from app.database import AppDatabase
from app.utils.events import Event, event_bus


class BaseService:
    """所有服务的基类。

    提供数据库引用和事件发布能力。
    子类应使用 self._db 访问数据库，使用 self._publish 发布事件。

    Attributes:
        _db: 数据库实例引用。
    """

    def __init__(self, db: AppDatabase) -> None:
        self._db = db
        self._logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

    def _publish(self, event: Event) -> None:
        """发布事件到事件总线。

        Args:
            event: 事件实例。
        """
        event_bus.publish(event)
