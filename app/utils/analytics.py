"""本地分析收集模块 -- 隐私优先的学习行为分析。

所有数据仅存储在本地 SQLite 数据库中，不上传任何内容。
不收集个人身份信息，仅记录聚合的行为指标。

跟踪的事件类型：
- 课程阅读时间
- 练习完成情况
- 连续学习天数
- 功能使用统计
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import date, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── 隐私常量 ──────────────────────────────────────────────────────────────────

# 不记录的具体字段
_EXCLUDED_FIELDS = frozenset({"api_key", "password", "token", "secret", "email", "username"})

# 数据保留天数（超过此天数的数据自动清理）
_RETENTION_DAYS = 90


def _sanitize_event_data(data: dict[str, Any]) -> dict[str, Any]:
    """移除敏感字段，确保隐私安全。"""
    return {k: v for k, v in data.items() if k.lower() not in _EXCLUDED_FIELDS}


def _anonymize_id(raw_id: str) -> str:
    """对标识符进行单向哈希，防止明文泄露。"""
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]


class AnalyticsCollector:
    """本地分析收集器。

    所有数据存储在应用数据库中，不会传输到外部。
    提供事件记录、聚合查询和自动清理功能。

    Attributes:
        _db: 数据库实例引用。
        _session_id: 当前会话标识（匿名哈希）。
        _enabled: 分析收集总开关。
    """

    def __init__(self, db: Any, enabled: bool = True) -> None:
        self._db = db
        self._enabled = enabled
        self._session_id = _anonymize_id(str(time.time()))
        self._session_start = time.monotonic()
        self._current_activity_start: Optional[float] = None
        self._current_activity_type: str = ""

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        logger.info("分析收集已%s", "启用" if value else "禁用")

    # ── 事件记录 ─────────────────────────────────────────────────────────────

    def track_event(self, event_type: str, data: Optional[dict[str, Any]] = None) -> None:
        """记录一个分析事件。

        Args:
            event_type: 事件类型标识。
            data: 事件相关数据（自动过滤敏感字段）。
        """
        if not self._enabled:
            return

        sanitized = _sanitize_event_data(data or {})
        try:
            self._db.record_analytics_event(
                event_type=event_type,
                session_id=self._session_id,
                data=sanitized,
            )
        except Exception as exc:
            logger.debug("记录分析事件失败: %s", exc)

    # ── 学习时间追踪 ─────────────────────────────────────────────────────────

    def start_activity(self, activity_type: str) -> None:
        """开始计时一个学习活动。"""
        self._current_activity_start = time.monotonic()
        self._current_activity_type = activity_type

    def end_activity(self, activity_type: str = "") -> float:
        """结束计时并记录活动持续时间（秒）。"""
        if self._current_activity_start is None:
            return 0.0

        elapsed = time.monotonic() - self._current_activity_start
        actual_type = activity_type or self._current_activity_type
        self._current_activity_start = None

        if elapsed > 1.0:  # 忽略不到1秒的活动
            self.track_event(
                "activity_time",
                {
                    "type": actual_type,
                    "duration_sec": round(elapsed, 1),
                },
            )
            # 同步到每日聚合
            try:
                self._db.update_daily_analytics(
                    date.today().isoformat(),
                    learning_time_sec=round(elapsed, 1),
                )
            except Exception as exc:
                logger.debug("更新每日分析失败: %s", exc)

        return elapsed

    # ── 课程追踪 ─────────────────────────────────────────────────────────────

    def track_lesson_completed(self, lesson_id: str, track_id: str) -> None:
        """记录课程完成。"""
        self.track_event(
            "lesson_completed",
            {
                "track_id": track_id,
            },
        )
        try:
            self._db.update_daily_analytics(
                date.today().isoformat(),
                lessons_completed=1,
            )
        except Exception as exc:
            logger.debug("更新每日课程计数失败: %s", exc)

    def track_lesson_opened(self, lesson_id: str, track_id: str) -> None:
        """记录课程打开。"""
        self.track_event("lesson_opened", {"track_id": track_id})

    # ── 练习追踪 ─────────────────────────────────────────────────────────────

    def track_exercise_attempt(self, exercise_id: str, score: int, passed: bool, duration_sec: int) -> None:
        """记录练习评测。"""
        self.track_event(
            "exercise_attempt",
            {
                "score": score,
                "passed": passed,
                "duration_sec": duration_sec,
            },
        )
        try:
            self._db.update_daily_analytics(
                date.today().isoformat(),
                exercises_completed=1,
                exercise_score_sum=score,
            )
        except Exception as exc:
            logger.debug("更新每日练习计数失败: %s", exc)

    # ── 功能使用追踪 ─────────────────────────────────────────────────────────

    def track_feature_usage(self, feature_name: str) -> None:
        """记录功能使用。"""
        self.track_event("feature_usage", {"feature": feature_name})

    # ── 聚合查询 ─────────────────────────────────────────────────────────────

    def get_learning_time_by_day(self, days: int = 30) -> list[dict[str, Any]]:
        """获取每天的学习时间。"""
        return self._db.get_analytics_daily_summary(days)

    def get_lessons_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """获取课程完成趋势。"""
        rows = self._db.get_analytics_daily_summary(days)
        return [{"date": r["date"], "count": r["lessons_completed"]} for r in rows]

    def get_exercise_performance(self, days: int = 30) -> list[dict[str, Any]]:
        """获取练习表现趋势。"""
        rows = self._db.get_analytics_daily_summary(days)
        result = []
        for r in rows:
            count = r["exercises_completed"]
            avg = round(r["exercise_score_sum"] / count) if count > 0 else 0
            result.append({"date": r["date"], "count": count, "avg_score": avg})
        return result

    def get_skill_distribution(self) -> dict[str, float]:
        """获取技能分布数据（用于雷达图）。

        基于各 track 的完成率和练习得分计算技能水平。
        """
        try:
            pass
        except Exception:
            return {}

        # 从数据库直接获取各 track 的完成数据
        try:
            track_stats = self._db.get_analytics_track_stats()
        except Exception:
            return {}

        return track_stats

    def get_streak_data(self, days: int = 90) -> list[dict[str, Any]]:
        """获取连续学习天数历史。"""
        rows = self._db.get_analytics_daily_summary(days)
        streak = 0
        result = []
        today = date.today()
        active_dates = {r["date"] for r in rows if (r["lessons_completed"] > 0 or r["exercises_completed"] > 0)}

        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            ds = d.isoformat()
            if ds in active_dates:
                streak += 1
            else:
                streak = 0
            result.append({"date": ds, "streak": streak})
        return result

    def generate_weekly_report(self) -> dict[str, Any]:
        """生成周报。"""
        data = self._db.get_analytics_daily_summary(7)
        total_time = sum(r["learning_time_sec"] for r in data)
        total_lessons = sum(r["lessons_completed"] for r in data)
        total_exercises = sum(r["exercises_completed"] for r in data)
        scores = [r["exercise_score_sum"] for r in data if r["exercises_completed"] > 0]
        counts = [r["exercises_completed"] for r in data if r["exercises_completed"] > 0]
        avg_score = round(sum(scores) / sum(counts)) if counts else 0
        active_days = sum(1 for r in data if r["lessons_completed"] > 0 or r["exercises_completed"] > 0)

        return {
            "period": "weekly",
            "total_learning_time_min": round(total_time / 60),
            "total_lessons_completed": total_lessons,
            "total_exercises_completed": total_exercises,
            "average_score": avg_score,
            "active_days": active_days,
            "daily_breakdown": data,
        }

    def generate_monthly_report(self) -> dict[str, Any]:
        """生成月报。"""
        data = self._db.get_analytics_daily_summary(30)
        total_time = sum(r["learning_time_sec"] for r in data)
        total_lessons = sum(r["lessons_completed"] for r in data)
        total_exercises = sum(r["exercises_completed"] for r in data)
        scores = [r["exercise_score_sum"] for r in data if r["exercises_completed"] > 0]
        counts = [r["exercises_completed"] for r in data if r["exercises_completed"] > 0]
        avg_score = round(sum(scores) / sum(counts)) if counts else 0
        active_days = sum(1 for r in data if r["lessons_completed"] > 0 or r["exercises_completed"] > 0)

        # 按周聚合
        weekly_data = []
        for i in range(0, 30, 7):
            week_slice = data[i : i + 7]
            weekly_data.append(
                {
                    "week_start": week_slice[0]["date"] if week_slice else "",
                    "lessons": sum(r["lessons_completed"] for r in week_slice),
                    "exercises": sum(r["exercises_completed"] for r in week_slice),
                    "time_min": round(sum(r["learning_time_sec"] for r in week_slice) / 60),
                }
            )

        return {
            "period": "monthly",
            "total_learning_time_min": round(total_time / 60),
            "total_lessons_completed": total_lessons,
            "total_exercises_completed": total_exercises,
            "average_score": avg_score,
            "active_days": active_days,
            "weekly_breakdown": weekly_data,
            "daily_breakdown": data,
        }

    # ── 数据清理 ─────────────────────────────────────────────────────────────

    def cleanup_old_data(self) -> int:
        """清理超过保留期的分析数据。"""
        try:
            cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).isoformat()
            return self._db.cleanup_analytics_before(cutoff)
        except Exception as exc:
            logger.debug("清理旧分析数据失败: %s", exc)
            return 0
