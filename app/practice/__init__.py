"""Practice module -- re-exports public names for convenience.

Submodules:
- practice.models:          Exercise and EvaluationResult dataclasses
- practice.exercise_loader: Exercise loading, fallback resolution, JSON resources
- practice.normalizer:      Row normalization for SQL result comparison
- practice.evaluator:       Code evaluation (SQL, keyword, Python)
"""

from app.practice.evaluator import (
    evaluate_keyword_code,
    evaluate_python,
    evaluate_sql,
    evaluate_sql_fixture,
    validate_sql_side_effect,
)
from app.practice.exercise_loader import (
    get_exercise_fallbacks,
    get_sql_query_fixtures,
    load_exercises,
    load_json_resource,
    needs_fallback,
)
from app.practice.models import EvaluationResult, Exercise
from app.practice.normalizer import normalize_rows

__all__ = [
    # models
    "Exercise",
    "EvaluationResult",
    # exercise_loader
    "load_json_resource",
    "get_exercise_fallbacks",
    "get_sql_query_fixtures",
    "needs_fallback",
    "load_exercises",
    # normalizer
    "normalize_rows",
    # evaluator
    "validate_sql_side_effect",
    "evaluate_sql_fixture",
    "evaluate_sql",
    "evaluate_keyword_code",
    "evaluate_python",
]
