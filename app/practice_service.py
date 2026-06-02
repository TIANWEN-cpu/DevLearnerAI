"""Backward-compatible shim -- logic has moved to app/practice/.

This module re-exports every public name so that existing imports like
``from app.practice_service import PracticeService`` continue to work.
New code should import directly from ``app.practice`` submodules.
"""

"""练习服务模块（向后兼容 shim）。

本模块是向后兼容的入口，将所有请求委托给 app.practice 子模块。
新代码应直接从 app.practice 子模块导入。

提供练习数据加载、按技术栈/难度筛选、以及多语言评测分发功能。
"""

import sqlite3
from pathlib import Path
from typing import Optional

from app.practice.evaluator import (
    evaluate_keyword_code,
    evaluate_python,
    evaluate_sql,
    evaluate_sql_fixture,
    validate_sql_side_effect,
)
from app.practice.exercise_loader import (
    get_exercise_fallbacks as _get_exercise_fallbacks,
)
from app.practice.exercise_loader import (
    get_sql_query_fixtures as _get_sql_query_fixtures,
)
from app.practice.exercise_loader import (
    load_exercises as _load_exercises,
)
from app.practice.exercise_loader import (
    needs_fallback as _needs_fallback,
)
from app.practice.models import EvaluationResult, Exercise
from app.practice.normalizer import normalize_rows

# ---------------------------------------------------------------------------
# PracticeService -- thin wrapper that delegates to the new modules
# ---------------------------------------------------------------------------


class PracticeService:
    """Practice service -- delegates to app.practice submodules."""

    def __init__(self, metadata_path: Optional[Path] = None) -> None:
        """初始化练习服务。

        加载练习元数据（可选指定元数据文件路径）。

        Args:
            metadata_path: 练习元数据 JSON 文件路径，默认使用 config.METADATA_DIR / exercises.json。
        """
        self.metadata_path = metadata_path
        self.exercises = _load_exercises(metadata_path)
        # Build indexes for O(1) filtering
        self._by_track: dict[str, list[Exercise]] = {}
        self._by_difficulty: dict[str, list[Exercise]] = {}
        self._by_id: dict[str, Exercise] = {}
        for ex in self.exercises:
            self._by_track.setdefault(ex.track_id, []).append(ex)
            self._by_difficulty.setdefault(ex.difficulty, []).append(ex)
            self._by_id[ex.id] = ex

    @staticmethod
    def _normalize_rows(rows: list, ordered: bool) -> list[tuple]:
        """标准化 SQL 结果行用于比较。

        Args:
            rows: 原始结果行列表。
            ordered: 是否保持原始顺序。

        Returns:
            标准化后的 tuple 列表。
        """
        return normalize_rows(rows, ordered)

    @staticmethod
    def _needs_fallback(value: str) -> bool:
        """检测文本是否需要使用回退值（包含编码损坏标记）。"""
        return _needs_fallback(value)

    @staticmethod
    def _validate_sql_side_effect(exercise_id: str, conn: sqlite3.Connection) -> bool:
        return validate_sql_side_effect(exercise_id, conn)

    def _evaluate_sql_fixture(self, exercise: Exercise, code: str, fixture: dict) -> EvaluationResult:
        return evaluate_sql_fixture(exercise, code, fixture)

    def _evaluate_sql(self, exercise: Exercise, code: str) -> EvaluationResult:
        return evaluate_sql(exercise, code)

    def _evaluate_keyword_code(self, exercise: Exercise, code: str) -> EvaluationResult:
        return evaluate_keyword_code(exercise, code)

    def _evaluate_python(self, exercise: Exercise, code: str) -> EvaluationResult:
        return evaluate_python(exercise, code)

    def evaluate(self, exercise: Exercise, code: str) -> EvaluationResult:
        """评测练习代码。

        根据练习所属技术栈自动分发到对应的评测器：
        - database: SQL 评测（内存数据库执行 + 结果比对）
        - c/csharp: 关键字结构检查
        - 其他: Python 沙箱执行评测

        Args:
            exercise: Exercise 实例。
            code: 用户提交的代码。

        Returns:
            EvaluationResult 评测结果。
        """
        if exercise.track_id == "database":
            return evaluate_sql(exercise, code)
        if exercise.track_id in {"c", "csharp"}:
            return evaluate_keyword_code(exercise, code)
        return evaluate_python(exercise, code)

    def filtered(self, track_id: str, difficulty: str) -> list[Exercise]:
        """按技术栈和难度筛选练习（使用索引加速）。

        Args:
            track_id: 技术栈 ID，传入 "all" 表示不过滤。
            difficulty: 难度级别，传入 "all" 表示不过滤。

        Returns:
            符合条件的 Exercise 列表。
        """
        if track_id != "all" and difficulty != "all":
            # Intersection: filter from the smaller set
            by_track = set(id(ex) for ex in self._by_track.get(track_id, []))
            return [ex for ex in self._by_difficulty.get(difficulty, []) if id(ex) in by_track]
        if track_id != "all":
            return list(self._by_track.get(track_id, []))
        if difficulty != "all":
            return list(self._by_difficulty.get(difficulty, []))
        return list(self.exercises)

    def exercise_by_id(self, exercise_id: str) -> Optional[Exercise]:
        """根据 ID 查找练习（O(1) 索引查找）。

        Args:
            exercise_id: 练习 ID。

        Returns:
            Exercise 实例，未找到时返回 None。
        """
        return self._by_id.get(exercise_id)


# ---------------------------------------------------------------------------
# Re-export private helpers that tests depend on
# ---------------------------------------------------------------------------
__all__ = [
    "PracticeService",
    "Exercise",
    "EvaluationResult",
    "_needs_fallback",
    "_get_exercise_fallbacks",
    "_get_sql_query_fixtures",
]
