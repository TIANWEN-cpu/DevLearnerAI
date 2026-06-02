"""Extended tests for app.practice.evaluator covering remaining paths.

Targets:
- validate_sql_side_effect with db-create-index-users-email (line 36 - invalid index name)
- validate_sql_side_effect with db-create-covering-index-report (line 49 - invalid index name)
- evaluate_sql_fixture explain mode (line 135)
- evaluate_sql_fixture side-effect mode (lines 137-142)
- evaluate_sql_fixture error handling
- PracticeService delegate methods
"""

import sqlite3
from unittest.mock import patch

import pytest

from app.practice.models import EvaluationResult, Exercise


@pytest.fixture
def make_exercise():
    """Factory to create Exercise instances."""

    def _make(**kwargs):
        defaults = {
            "id": "test-ex",
            "title": "Test Exercise",
            "track_id": "python",
            "difficulty": "easy",
            "prompt": "Test",
            "lesson_id": "l1",
            "required_keywords": [],
            "forbidden_keywords": [],
            "starter_code": "",
            "hints": [],
            "expected_nodes": [],
            "required_names": [],
            "tests": [],
        }
        defaults.update(kwargs)
        return Exercise(**defaults)

    return _make


class TestValidateSqlSideEffectExtended:
    """Test validate_sql_side_effect for various exercise IDs."""

    def test_db_create_index_with_invalid_index_name(self, make_exercise):
        """Index names with special chars should be skipped by re.fullmatch."""
        from app.practice.evaluator import validate_sql_side_effect

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT)")
        conn.execute('CREATE INDEX "idx-users-email!!!" ON users(email)')
        result = validate_sql_side_effect("db-create-index-users-email", conn)
        assert result is False
        conn.close()

    def test_db_create_covering_index_with_invalid_name(self, make_exercise):
        """Covering index with invalid name should be skipped."""
        from app.practice.evaluator import validate_sql_side_effect

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER)")
        conn.execute('CREATE INDEX "bad!!name" ON reports(created_at, status)')
        result = validate_sql_side_effect("db-create-covering-index-report", conn)
        assert result is False
        conn.close()

    def test_unknown_exercise_id_returns_false(self):
        from app.practice.evaluator import validate_sql_side_effect

        conn = sqlite3.connect(":memory:")
        result = validate_sql_side_effect("unknown-exercise", conn)
        assert result is False
        conn.close()

    def test_db_explain_users_query(self):
        from app.practice.evaluator import validate_sql_side_effect

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT)")
        result = validate_sql_side_effect("db-explain-users-query", conn)
        assert isinstance(result, bool)
        conn.close()


class TestEvaluateSqlFixtureExtended:
    """Test evaluate_sql_fixture edge cases."""

    def test_empty_code_returns_empty_result(self, make_exercise):
        from app.practice.evaluator import evaluate_sql_fixture

        exercise = make_exercise(required_keywords=["SELECT"])
        fixture = {"setup": "", "expected_rows": [], "mode": "query"}
        result = evaluate_sql_fixture(exercise, "", fixture)
        assert result.passed is False
        assert any("空" in f for f in result.feedback_lines)

    def test_explain_mode_success(self, make_exercise):
        """Test explain mode returns non-empty plan rows."""
        from app.practice.evaluator import evaluate_sql_fixture

        exercise = make_exercise(
            id="db-explain-users-query",
            required_keywords=["EXPLAIN"],
        )
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);",
            "mode": "explain",
        }
        result = evaluate_sql_fixture(
            exercise,
            "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@example.com'",
            fixture,
        )
        assert any("执行计划" in f or "EXPLAIN" in f for f in result.feedback_lines)

    def test_side_effect_mode_success(self, make_exercise):
        """Test DDL side-effect mode with valid schema change."""
        from app.practice.evaluator import evaluate_sql_fixture

        exercise = make_exercise(
            id="db-add-column-migration",
            required_keywords=["ALTER"],
        )
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);",
            "mode": "side_effect",
        }
        result = evaluate_sql_fixture(
            exercise,
            "ALTER TABLE users ADD COLUMN last_login TEXT;",
            fixture,
        )
        assert any("结构变更" in f or "通过" in f for f in result.feedback_lines)

    def test_side_effect_mode_failure(self, make_exercise):
        """Test DDL side-effect mode when schema change doesn't meet requirements."""
        from app.practice.evaluator import evaluate_sql_fixture

        exercise = make_exercise(
            id="db-add-column-migration",
            required_keywords=["ALTER"],
        )
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);",
            "mode": "side_effect",
        }
        result = evaluate_sql_fixture(
            exercise,
            "ALTER TABLE users ADD COLUMN wrong_col TEXT;",
            fixture,
        )
        assert any("还没有达到" in f for f in result.feedback_lines)


class TestEvaluateSqlExtended:
    """Test the evaluate_sql function with various exercise types."""

    def test_unknown_exercise_falls_through(self, make_exercise):
        """Unknown exercise IDs should get default fixture."""
        from app.practice.evaluator import evaluate_sql

        exercise = make_exercise(
            id="unknown-sql-exercise",
            required_keywords=["SELECT"],
        )
        result = evaluate_sql(exercise, "SELECT 1")
        assert isinstance(result, EvaluationResult)

    def test_sql_execution_error(self, make_exercise):
        """Invalid SQL should report execution error."""
        from app.practice.evaluator import evaluate_sql_fixture

        exercise = make_exercise(required_keywords=["SELECT"])
        fixture = {"setup": "", "expected_rows": [], "mode": "query"}
        result = evaluate_sql_fixture(exercise, "INVALID SQL SYNTAX", fixture)
        assert any("失败" in f or "执行失败" in f for f in result.feedback_lines)


class TestPracticeServiceDelegates:
    """Test PracticeService wrapper methods (lines 77, 93)."""

    def test_evaluate_delegates(self, make_exercise):
        from app.practice_service import PracticeService

        svc = PracticeService()
        exercise = make_exercise(
            track_id="python",
            required_keywords=["def"],
            starter_code="",
        )
        with patch(
            "app.practice.evaluator.evaluate_python_code",
            return_value={"passed": True, "score": 100, "feedback_lines": ["ok"], "stdout": "", "duration_sec": 0},
        ):
            result = svc.evaluate(exercise, "def f(): pass")
        assert isinstance(result, EvaluationResult)
