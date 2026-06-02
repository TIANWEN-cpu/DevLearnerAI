"""Backward-compatible shim -- logic has moved to app/practice/.

This module re-exports every public name so that existing imports like
``from app.practice_service import PracticeService`` continue to work.
New code should import directly from ``app.practice`` submodules.
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
        self.metadata_path = metadata_path
        self.exercises = _load_exercises(metadata_path)

    @staticmethod
    def _normalize_rows(rows: list, ordered: bool) -> list[tuple]:
        return normalize_rows(rows, ordered)

    @staticmethod
    def _needs_fallback(value: str) -> bool:
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
        if exercise.track_id == "database":
            return evaluate_sql(exercise, code)
        if exercise.track_id in {"c", "csharp"}:
            return evaluate_keyword_code(exercise, code)
        return evaluate_python(exercise, code)

    def filtered(self, track_id: str, difficulty: str) -> list[Exercise]:
        results = self.exercises
        if track_id != "all":
            results = [ex for ex in results if ex.track_id == track_id]
        if difficulty != "all":
            results = [ex for ex in results if ex.difficulty == difficulty]
        return results

    def exercise_by_id(self, exercise_id: str) -> Optional[Exercise]:
        return next((item for item in self.exercises if item.id == exercise_id), None)


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
