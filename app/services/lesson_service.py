"""课程进度服务 -- 管理课程打开、完成、状态查询。"""

from __future__ import annotations

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import LessonCompletedEvent, LessonOpenedEvent


class LessonService(BaseService):
    """课程进度管理服务。

    封装 AppDatabase 中课程相关操作，通过事件总线发布状态变更。
    """

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def mark_opened(self, lesson_id: str, track_id: str) -> None:
        """标记课程为已打开。"""
        self._db.mark_lesson_opened(lesson_id, track_id)
        self._publish(LessonOpenedEvent(lesson_id=lesson_id, track_id=track_id))

    def mark_completed(self, lesson_id: str, track_id: str) -> None:
        """标记课程为已完成。"""
        self._db.mark_lesson_completed(lesson_id, track_id)
        self._publish(LessonCompletedEvent(lesson_id=lesson_id, track_id=track_id))

    def get_status(self, lesson_id: str) -> str:
        """查询课程状态。

        Returns:
            'not_started'、'in_progress' 或 'completed'。
        """
        return self._db.lesson_status(lesson_id)

    def get_track_completion(self, track_id: str) -> int:
        """统计技术栈已完成课程数。"""
        return self._db.track_completion(track_id)

    def get_completed_count(self) -> int:
        """统计所有已完成课程总数。"""
        return self._db.completed_lessons()

    def list_completed(self) -> list[tuple]:
        """列出所有已完成课程。"""
        return self._db.list_completed_lessons()

    def get_streak(self) -> int:
        """获取连续学习天数。"""
        return self._db.active_days_streak()
