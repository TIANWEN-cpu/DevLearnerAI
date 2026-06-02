"""复习服务 -- 管理间隔复习计划（SM-2 算法）。"""

from __future__ import annotations

from typing import Optional

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import ReviewCompletedEvent


class ReviewService(BaseService):
    """间隔复习管理服务。"""

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def update_schedule(self, exercise_id: str, quality: int) -> None:
        """更新复习计划。

        Args:
            exercise_id: 练习 ID。
            quality: 回忆质量 0-5。
        """
        self._db.update_review_schedule(exercise_id, quality)
        self._publish(ReviewCompletedEvent(exercise_id=exercise_id, quality=quality))

    def get_schedule(self, exercise_id: str) -> Optional[dict]:
        """获取练习的复习计划。"""
        return self._db.get_review_schedule(exercise_id)

    def get_due_exercises(self, limit: int = 20) -> list[tuple]:
        """获取今天需要复习的练习。"""
        return self._db.exercises_due_for_review(limit)

    def get_today_count(self) -> int:
        """今天已完成的复习数量。"""
        return self._db.review_count_today()

    def get_total_count(self) -> int:
        """总复习次数。"""
        return self._db.total_review_count()
