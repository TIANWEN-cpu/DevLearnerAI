"""Extended tests for app.practice_service -- internal helpers and evaluation logic.

Covers:
- _needs_fallback (encoding corruption detection)
- EvaluationResult.feedback_text property
- _validate_sql_side_effect (DDL validation branches)
- _evaluate_keyword_code (keyword-based code evaluation)
- _evaluate_sql_fixture (full SQL fixture evaluation pipeline)
- _evaluate_sql (dispatcher + DDL-only exercises)
- filtered / exercise_by_id (exercise query helpers)
"""

import sqlite3

import pytest

from app.practice_service import (
    EvaluationResult,
    Exercise,
    PracticeService,
    _needs_fallback,
)


# ---------------------------------------------------------------------------
# _needs_fallback
# ---------------------------------------------------------------------------
class TestNeedsFallback:
    """Test the encoding-corruption detector used during exercise loading."""

    def test_normal_text_no_fallback(self):
        assert _needs_fallback("正常中文文本") is False

    def test_empty_string_no_fallback(self):
        assert _needs_fallback("") is False

    def test_question_mark_triggers_fallback(self):
        assert _needs_fallback("???") is True

    def test_mixed_question_and_garble_triggers_fallback(self):
        assert _needs_fallback("显示?完成") is True

    def test_pure_ascii_no_fallback(self):
        assert _needs_fallback("hello world") is False

    def test_single_question_mark_triggers_fallback(self):
        assert _needs_fallback("?") is True


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------
class TestEvaluationResult:
    """Test the EvaluationResult dataclass and its property."""

    def test_feedback_text_joins_lines(self):
        result = EvaluationResult(passed=True, score=100, feedback_lines=["line1", "line2", "line3"])
        assert result.feedback_text == "line1\nline2\nline3"

    def test_feedback_text_empty_lines(self):
        result = EvaluationResult(passed=False, score=0, feedback_lines=[])
        assert result.feedback_text == ""

    def test_defaults(self):
        result = EvaluationResult(passed=False, score=0, feedback_lines=["a"])
        assert result.stdout == ""
        assert result.duration_sec == 0

    def test_pass_threshold(self):
        result = EvaluationResult(passed=True, score=70, feedback_lines=["ok"])
        assert result.passed is True

    def test_fail_threshold(self):
        result = EvaluationResult(passed=False, score=69, feedback_lines=["fail"])
        assert result.passed is False


# ---------------------------------------------------------------------------
# _validate_sql_side_effect
# ---------------------------------------------------------------------------
class TestValidateSqlSideEffect:
    """Test DDL validation for various SQL exercises against in-memory SQLite."""

    @pytest.fixture()
    def conn(self):
        c = sqlite3.connect(":memory:")
        c.execute("PRAGMA foreign_keys = ON")
        yield c
        c.close()

    def test_design_enrollment_table_pass(self, conn):
        conn.execute("CREATE TABLE enrollments(student_id INTEGER, course_id INTEGER)")
        assert PracticeService._validate_sql_side_effect("db-design-enrollment-table", conn) is True

    def test_design_enrollment_table_fail_missing_column(self, conn):
        conn.execute("CREATE TABLE enrollments(student_id INTEGER)")
        assert PracticeService._validate_sql_side_effect("db-design-enrollment-table", conn) is False

    def test_orders_foreign_key_pass(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute(
            "CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id))"
        )
        assert PracticeService._validate_sql_side_effect("db-orders-foreign-key", conn) is True

    def test_orders_foreign_key_fail_no_fk(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER)")
        assert PracticeService._validate_sql_side_effect("db-orders-foreign-key", conn) is False

    def test_create_index_users_email_pass(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT)")
        conn.execute("CREATE INDEX idx_users_email ON users(email)")
        assert PracticeService._validate_sql_side_effect("db-create-index-users-email", conn) is True

    def test_create_index_users_email_fail(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT)")
        assert PracticeService._validate_sql_side_effect("db-create-index-users-email", conn) is False

    def test_add_column_migration_pass(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        assert PracticeService._validate_sql_side_effect("db-add-column-migration", conn) is True

    def test_add_column_migration_fail(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        assert PracticeService._validate_sql_side_effect("db-add-column-migration", conn) is False

    def test_create_covering_index_report_pass(self, conn):
        conn.execute("CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER)")
        conn.execute("CREATE INDEX idx_reports_cover ON reports(created_at, status)")
        assert PracticeService._validate_sql_side_effect("db-create-covering-index-report", conn) is True

    def test_create_covering_index_report_fail_wrong_columns(self, conn):
        conn.execute("CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER)")
        conn.execute("CREATE INDEX idx_reports_wrong ON reports(owner_id)")
        assert PracticeService._validate_sql_side_effect("db-create-covering-index-report", conn) is False

    def test_add_status_column_users_pass(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT")
        assert PracticeService._validate_sql_side_effect("db-add-status-column-users", conn) is True

    def test_add_status_column_users_fail(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        assert PracticeService._validate_sql_side_effect("db-add-status-column-users", conn) is False

    def test_create_enrollment_foreign_key_pass(self, conn):
        conn.execute("CREATE TABLE students(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT)")
        conn.execute(
            "CREATE TABLE enrollments("
            "student_id INTEGER, course_id INTEGER, "
            "FOREIGN KEY(student_id) REFERENCES students(id), "
            "FOREIGN KEY(course_id) REFERENCES courses(id))"
        )
        assert PracticeService._validate_sql_side_effect("db-create-enrollment-foreign-key", conn) is True

    def test_create_enrollment_foreign_key_fail_partial_fk(self, conn):
        conn.execute("CREATE TABLE students(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT)")
        conn.execute(
            "CREATE TABLE enrollments("
            "student_id INTEGER, course_id INTEGER, "
            "FOREIGN KEY(student_id) REFERENCES students(id))"
        )
        assert PracticeService._validate_sql_side_effect("db-create-enrollment-foreign-key", conn) is False

    def test_explain_users_query_pass(self, conn):
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT)")
        conn.execute("INSERT INTO users(email) VALUES ('a@test.com')")
        assert PracticeService._validate_sql_side_effect("db-explain-users-query", conn) is True

    def test_unknown_exercise_returns_false(self, conn):
        assert PracticeService._validate_sql_side_effect("unknown-exercise-id", conn) is False


# ---------------------------------------------------------------------------
# _evaluate_keyword_code
# ---------------------------------------------------------------------------
class TestEvaluateKeywordCode:
    """Test keyword-based evaluation for C and C# exercises."""

    def _make_exercise(self, **overrides) -> Exercise:
        defaults = {
            "id": "test-ex",
            "title": "Test",
            "track_id": "c",
            "difficulty": "精选",
            "prompt": "Test prompt",
            "lesson_id": "lesson-1",
            "required_keywords": ["int", "main"],
            "forbidden_keywords": ["goto"],
            "hints": [],
            "starter_code": "",
            "expected_nodes": [],
            "required_names": [],
            "tests": [],
        }
        defaults.update(overrides)
        return Exercise(**defaults)

    def test_empty_code_fails(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        result = svc._evaluate_keyword_code(ex, "")
        assert result.passed is False
        assert result.score < 70

    def test_code_with_required_keywords_scores_high(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        result = svc._evaluate_keyword_code(ex, "int main() { return 0; }")
        assert result.score >= 70
        assert result.passed is True

    def test_missing_required_keyword_reduces_score(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(required_keywords=["int", "printf"])
        result = svc._evaluate_keyword_code(ex, "int main() { }")
        assert "printf" in str(result.feedback_lines)
        assert result.passed is False

    def test_forbidden_keyword_reported_in_feedback(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(forbidden_keywords=["goto"])
        result = svc._evaluate_keyword_code(ex, "int main() { goto end; }")
        assert "goto" in str(result.feedback_lines)
        assert "不建议" in str(result.feedback_lines)

    def test_all_required_and_no_forbidden_scores_high(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(
            required_keywords=["int", "main", "printf"],
            forbidden_keywords=["goto"],
        )
        result = svc._evaluate_keyword_code(ex, 'int main() { printf("hi"); }')
        assert result.passed is True
        assert result.score >= 90

    def test_no_forbidden_keywords_bonus(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(forbidden_keywords=[])
        result = svc._evaluate_keyword_code(ex, "int main() { return 0; }")
        assert "禁用" in str(result.feedback_lines) or result.score >= 90

    def test_semicolon_bonus(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(required_keywords=["int"])
        result = svc._evaluate_keyword_code(ex, "int x = 1;")
        assert result.score >= 30  # 20 (submitted) + 10 (semicolon/format)

    def test_brace_bonus(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(required_keywords=["int"])
        result = svc._evaluate_keyword_code(ex, "int main() { }")
        assert result.score >= 30


# ---------------------------------------------------------------------------
# _evaluate_sql_fixture (pipeline)
# ---------------------------------------------------------------------------
class TestEvaluateSqlFixture:
    """Test the full SQL fixture evaluation pipeline."""

    def _make_exercise(self, **overrides) -> Exercise:
        defaults = {
            "id": "db-select-active",
            "title": "Test SQL",
            "track_id": "database",
            "difficulty": "精选",
            "prompt": "Test",
            "lesson_id": "lesson-1",
            "required_keywords": ["select"],
            "forbidden_keywords": [],
            "hints": [],
            "starter_code": "",
            "expected_nodes": [],
            "required_names": [],
            "tests": [],
        }
        defaults.update(overrides)
        return Exercise(**defaults)

    def _make_fixture(self) -> dict:
        return {
            "setup": """
                CREATE TABLE users(name TEXT, status TEXT);
                INSERT INTO users(name, status) VALUES
                    ('Ada', 'active'),
                    ('Ben', 'inactive'),
                    ('Mina', 'active');
            """,
            "expected_rows": [("Ada",), ("Mina",)],
            "ordered": True,
        }

    def test_correct_query_passes(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        fixture = self._make_fixture()
        result = svc._evaluate_sql_fixture(
            ex,
            "SELECT name FROM users WHERE status = 'active' ORDER BY name;",
            fixture,
        )
        assert result.passed is True
        assert result.score >= 90

    def test_wrong_result_fails(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        fixture = self._make_fixture()
        result = svc._evaluate_sql_fixture(
            ex,
            "SELECT name FROM users WHERE status = 'inactive';",
            fixture,
        )
        assert result.passed is False
        assert "不一致" in str(result.feedback_lines)

    def test_empty_code_fails(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        fixture = self._make_fixture()
        result = svc._evaluate_sql_fixture(ex, "", fixture)
        assert result.passed is False
        assert result.score == 0

    def test_missing_required_keyword_reduces_score(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(required_keywords=["select", "where"])
        fixture = self._make_fixture()
        result = svc._evaluate_sql_fixture(
            ex,
            "SELECT name FROM users;",
            fixture,
        )
        assert "where" in str(result.feedback_lines).lower()

    def test_script_mode_fixture(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(required_keywords=["begin", "update", "commit"])
        fixture = {
            "setup": """
                CREATE TABLE accounts(id INTEGER PRIMARY KEY, balance INTEGER);
                INSERT INTO accounts(id, balance) VALUES (1, 100), (2, 80);
            """,
            "mode": "script",
            "check_sql": "SELECT id, balance FROM accounts ORDER BY id;",
            "expected_rows": [(1, 70), (2, 110)],
            "ordered": True,
        }
        code = "BEGIN; UPDATE accounts SET balance = balance - 30 WHERE id = 1; UPDATE accounts SET balance = balance + 30 WHERE id = 2; COMMIT;"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        assert result.passed is True

    def test_syntax_error_in_sql(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        fixture = self._make_fixture()
        result = svc._evaluate_sql_fixture(ex, "SELCT * FORM users;", fixture)
        assert result.passed is False
        assert "执行失败" in str(result.feedback_lines)

    def test_semicolon_bonus_in_fixture(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise()
        fixture = self._make_fixture()
        result_with = svc._evaluate_sql_fixture(
            ex,
            "SELECT name FROM users WHERE status = 'active' ORDER BY name;",
            fixture,
        )
        result_without = svc._evaluate_sql_fixture(
            ex,
            "SELECT name FROM users WHERE status = 'active' ORDER BY name",
            fixture,
        )
        assert result_with.score >= result_without.score


# ---------------------------------------------------------------------------
# _evaluate_sql dispatcher
# ---------------------------------------------------------------------------
class TestEvaluateSqlDispatcher:
    """Test the _evaluate_sql method that dispatches to fixture or DDL evaluation."""

    def _make_exercise(self, exercise_id: str, **overrides) -> Exercise:
        defaults = {
            "id": exercise_id,
            "title": "Test",
            "track_id": "database",
            "difficulty": "精选",
            "prompt": "Test",
            "lesson_id": "lesson-1",
            "required_keywords": [],
            "forbidden_keywords": [],
            "hints": [],
            "starter_code": "",
            "expected_nodes": [],
            "required_names": [],
            "tests": [],
        }
        defaults.update(overrides)
        return Exercise(**defaults)

    def test_ddl_exercise_enrollment_table(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("db-design-enrollment-table")
        code = "CREATE TABLE enrollments(student_id INTEGER, course_id INTEGER);"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_ddl_exercise_add_column(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("db-add-column-migration")
        code = "ALTER TABLE users ADD COLUMN last_login TEXT;"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_ddl_exercise_create_index(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("db-create-index-users-email")
        code = "CREATE INDEX idx_email ON users(email);"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_ddl_exercise_add_status_column(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("db-add-status-column-users")
        code = "ALTER TABLE users ADD COLUMN status TEXT;"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_ddl_exercise_explain_query(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("db-explain-users-query")
        code = "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@example.com';"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_unknown_sql_exercise_uses_structure_check(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(
            "unknown-sql-ex",
            required_keywords=["select", "join"],
        )
        code = "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id;"
        result = svc._evaluate_sql(ex, code)
        assert result.score > 0
        assert result.passed is True

    def test_structure_check_empty_code(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise("unknown-sql-ex", required_keywords=["select"])
        result = svc._evaluate_sql(ex, "")
        assert result.passed is False

    def test_structure_check_with_forbidden_keyword_reported(self):
        svc = PracticeService.__new__(PracticeService)
        ex = self._make_exercise(
            "unknown-sql-ex",
            required_keywords=["select"],
            forbidden_keywords=["drop"],
        )
        code = "SELECT * FROM t; DROP TABLE t;"
        result = svc._evaluate_sql(ex, code)
        assert "drop" in str(result.feedback_lines).lower()
        # Forbidden keywords are reported but do not block pass in structure-only mode
        assert result.score >= 20
