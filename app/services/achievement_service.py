"""成就服务 -- 管理成就解锁和进度查询。"""

from __future__ import annotations

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import AchievementUnlockedEvent


class AchievementService(BaseService):
    """成就管理服务。"""

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def list_all(self) -> list[dict]:
        """列出所有成就及其进度。"""
        return self._db.list_achievements()

    def unlocked_count(self) -> int:
        """已解锁成就数量。"""
        return self._db.unlocked_achievements_count()

    def update_progress(self, achievement_id: str, value: int) -> bool:
        """更新成就进度。

        Returns:
            True 表示刚解锁。
        """
        unlocked = self._db.update_achievement_progress(achievement_id, value)
        if unlocked:
            ach = self._db.fetchone(
                "SELECT title, description FROM achievements WHERE id = ?",
                (achievement_id,),
            )
            title = ach[0] if ach else achievement_id
            desc = ach[1] if ach else ""
            self._publish(
                AchievementUnlockedEvent(
                    achievement_id=achievement_id,
                    title=title,
                    description=desc,
                )
            )
        return unlocked

    def check_streak(self) -> list[str]:
        """检查连续学习成就。返回新解锁的 ID 列表。"""
        return self._db.check_streak_achievements()

    def check_completion(self) -> list[str]:
        """检查课程完成成就。返回新解锁的 ID 列表。"""
        return self._db.check_completion_achievements()

    def check_practice(self) -> list[str]:
        """检查练习相关成就。返回新解锁的 ID 列表。"""
        return self._db.check_practice_achievements()
