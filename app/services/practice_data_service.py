"""练习数据服务 -- 管理练习记录、草稿、统计。"""

from __future__ import annotations

from typing import Optional

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import (
    ExerciseAttemptRecordedEvent,
    ExerciseDraftClearedEvent,
    ExerciseDraftSavedEvent,
)


class PracticeDataService(BaseService):
    """练习数据管理服务。

    封装 AppDatabase 中练习相关操作，通过事件总线发布状态变更。
    """

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def record_attempt(
        self,
        exercise_id: str,
        exercise_title: str,
        track_id: str,
        code: str,
        score: int,
        passed: bool,
        duration_sec: int,
        feedback: str,
    ) -> None:
        """记录练习评测结果。"""
        self._db.record_attempt(exercise_id, exercise_title, track_id, code, score, passed, duration_sec, feedback)
        self._publish(
            ExerciseAttemptRecordedEvent(
                exercise_id=exercise_id,
                score=score,
                passed=passed,
                duration_sec=duration_sec,
            )
        )

    def record_batch(self, records: list[tuple]) -> None:
        """批量记录练习结果。"""
        self._db.record_attempts_batch(records)

    def save_draft(self, exercise_id: str, title: str, code: str) -> None:
        """保存练习草稿。"""
        self._db.save_exercise_draft(exercise_id, title, code)
        self._publish(ExerciseDraftSavedEvent(exercise_id=exercise_id))

    def load_draft(self, exercise_id: str) -> Optional[tuple[str, str]]:
        """加载练习草稿。

        Returns:
            (title, code) 元组，不存在时返回 None。
        """
        return self._db.load_exercise_draft(exercise_id)

    def clear_draft(self, exercise_id: str) -> None:
        """清除练习草稿。"""
        self._db.clear_exercise_draft(exercise_id)
        self._publish(ExerciseDraftClearedEvent(exercise_id=exercise_id))

    def get_recent_attempts(self, limit: int = 10) -> list[tuple]:
        """获取最近练习记录。"""
        return self._db.recent_attempts(limit)

    def get_average_score(self) -> int:
        """获取平均分。"""
        return self._db.average_score()

    def record_timer(self, exercise_id: str, duration_sec: int, difficulty: str = "") -> None:
        """记录练习用时。"""
        self._db.record_exercise_timer(exercise_id, duration_sec, difficulty)

    def get_timer_history(self, exercise_id: str) -> list[tuple]:
        """获取练习历史用时。"""
        return self._db.exercise_timer_history(exercise_id)
