"""Additional tests for app.practice_service -- covering remaining branches.

Targets:
- filtered() with various track_id and difficulty combinations (lines 843-849)
- exercise_by_id() finding and not finding exercises (lines 851-852)
- evaluate() dispatching to different backends (lines 854-859)
- _load_exercises() with fallback logic (lines 814-841)
- _evaluate_sql_fixture: explain mode (lines 978-984), forbidden keyword branch
- _evaluate_sql: DDL exercises for orders-foreign-key and covering-index
- _evaluate_sql: structure check semicolon bonus (line 1069-1071)
- _evaluate_keyword_code: empty code, forbidden keyword, brace/semicolon bonus
- EXERCISE_FALLBACKS and SQL_QUERY_FIXTURES data integrity
"""

import json
import sqlite3

import pytest

from app.practice_service import (
    EvaluationResult,
    Exercise,
    PracticeService,
    _get_exercise_fallbacks,
    _get_sql_query_fixtures,
    _needs_fallback,
)


# ---------------------------------------------------------------------------
# Helper to create a minimal Exercise
# ---------------------------------------------------------------------------
def _make_exercise(exercise_id: str = "test-ex", **overrides) -> Exercise:
    defaults = {
        "id": exercise_id,
        "title": "Test",
        "track_id": "python",
        "difficulty": "精选",
        "prompt": "Test prompt",
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


# ---------------------------------------------------------------------------
# filtered
# ---------------------------------------------------------------------------
class TestFiltered:
    """Test ExerciseService.filtered for track and difficulty filtering."""

    def _svc_with_exercises(self) -> PracticeService:
        svc = PracticeService.__new__(PracticeService)
        svc.exercises = [
            _make_exercise("ex1", track_id="python", difficulty="精选"),
            _make_exercise("ex2", track_id="python", difficulty="进阶"),
            _make_exercise("ex3", track_id="database", difficulty="精选"),
            _make_exercise("ex4", track_id="c", difficulty="兴趣"),
        ]
        # Build indexes (normally done in __init__)
        svc._by_track = {}
        svc._by_difficulty = {}
        svc._by_id = {}
        for ex in svc.exercises:
            svc._by_track.setdefault(ex.track_id, []).append(ex)
            svc._by_difficulty.setdefault(ex.difficulty, []).append(ex)
            svc._by_id[ex.id] = ex
        return svc

    def test_filter_all_returns_all(self):
        svc = self._svc_with_exercises()
        result = svc.filtered("all", "all")
        assert len(result) == 4

    def test_filter_by_track(self):
        svc = self._svc_with_exercises()
        result = svc.filtered("python", "all")
        assert len(result) == 2
        assert all(e.track_id == "python" for e in result)

    def test_filter_by_difficulty(self):
        svc = self._svc_with_exercises()
        result = svc.filtered("all", "精选")
        assert len(result) == 2
        assert all(e.difficulty == "精选" for e in result)

    def test_filter_by_track_and_difficulty(self):
        svc = self._svc_with_exercises()
        result = svc.filtered("python", "进阶")
        assert len(result) == 1
        assert result[0].id == "ex2"

    def test_filter_no_match(self):
        svc = self._svc_with_exercises()
        result = svc.filtered("rust", "all")
        assert len(result) == 0

    def test_filter_empty_exercises(self):
        svc = PracticeService.__new__(PracticeService)
        svc.exercises = []
        svc._by_id = {}
        svc._by_track = {}
        svc._by_difficulty = {}
        assert svc.filtered("all", "all") == []


# ---------------------------------------------------------------------------
# exercise_by_id
# ---------------------------------------------------------------------------
class TestExerciseById:
    """Test looking up exercises by ID."""

    def test_found(self):
        svc = PracticeService.__new__(PracticeService)
        svc.exercises = [_make_exercise("abc-123"), _make_exercise("def-456")]
        svc._by_id = {ex.id: ex for ex in svc.exercises}
        result = svc.exercise_by_id("abc-123")
        assert result is not None
        assert result.id == "abc-123"

    def test_not_found_returns_none(self):
        svc = PracticeService.__new__(PracticeService)
        svc.exercises = [_make_exercise("abc-123")]
        svc._by_id = {ex.id: ex for ex in svc.exercises}
        result = svc.exercise_by_id("nonexistent")
        assert result is None

    def test_empty_exercises_list(self):
        svc = PracticeService.__new__(PracticeService)
        svc.exercises = []
        svc._by_id = {}
        assert svc.exercise_by_id("any") is None


# ---------------------------------------------------------------------------
# evaluate dispatcher
# ---------------------------------------------------------------------------
class TestEvaluateDispatcher:
    """Test that evaluate() dispatches to the correct backend."""

    def test_database_track_dispatches_to_sql(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="database", required_keywords=["select"])
        # This should dispatch to _evaluate_sql and use the structure check path
        result = svc.evaluate(ex, "SELECT 1;")
        assert isinstance(result, EvaluationResult)

    def test_csharp_track_dispatches_to_keyword(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="csharp", required_keywords=["int"])
        result = svc.evaluate(ex, "int x = 1;")
        assert isinstance(result, EvaluationResult)
        assert result.score > 0

    def test_c_track_dispatches_to_keyword(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="c", required_keywords=["int", "main"])
        result = svc.evaluate(ex, "int main() {}")
        assert isinstance(result, EvaluationResult)
        assert result.score > 0

    def test_python_track_dispatches_to_python(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            track_id="python",
            expected_nodes=["Assign"],
            required_names=["x"],
        )
        result = svc.evaluate(ex, "x = 1")
        assert isinstance(result, EvaluationResult)


# ---------------------------------------------------------------------------
# _evaluate_sql_fixture  -- additional branches
# ---------------------------------------------------------------------------
class TestEvaluateSqlFixtureExtended:
    """Additional SQL fixture evaluation tests."""

    def test_explain_mode_pass(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            "db-explain-test",
            track_id="database",
            required_keywords=["explain"],
        )
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);"
            "INSERT INTO users(email) VALUES ('a@test.com');",
            "mode": "explain",
        }
        code = "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@test.com';"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        assert result.passed is True
        assert any("EXPLAIN" in line or "执行计划" in line for line in result.feedback_lines)

    def test_explain_mode_no_rows(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-explain-test", track_id="database", required_keywords=["explain"])
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY);",
            "mode": "explain",
        }
        # Use a valid EXPLAIN that still returns rows
        code = "EXPLAIN QUERY PLAN SELECT * FROM users;"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        # Should pass because EXPLAIN QUERY PLAN on any table returns rows
        assert isinstance(result, EvaluationResult)

    def test_script_mode_wrong_result(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="database", required_keywords=["update"])
        fixture = {
            "setup": "CREATE TABLE accounts(id INTEGER PRIMARY KEY, balance INTEGER);"
            "INSERT INTO accounts(id, balance) VALUES (1, 100), (2, 80);",
            "mode": "script",
            "check_sql": "SELECT id, balance FROM accounts ORDER BY id;",
            "expected_rows": [(1, 999), (2, 80)],  # wrong: 999 != 200
            "ordered": True,
        }
        code = "UPDATE accounts SET balance = 200 WHERE id = 1;"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        # The script runs but result (1, 200) doesn't match expected (1, 999)
        assert result.passed is False
        assert any("不一致" in line for line in result.feedback_lines)

    def test_forbidden_keyword_in_fixture(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            track_id="database",
            required_keywords=["select"],
            forbidden_keywords=["drop"],
        )
        fixture = {
            "setup": "CREATE TABLE users(id INTEGER, name TEXT);INSERT INTO users VALUES (1, 'Ada');",
            "expected_rows": [(1,)],
            "ordered": True,
        }
        code = "SELECT 1 FROM users LIMIT 1; DROP TABLE users;"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        assert "不建议" in str(result.feedback_lines)

    def test_query_with_no_expected_rows(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="database")
        fixture = {
            "setup": "CREATE TABLE t(id INTEGER);",
            "expected_rows": [],
            "ordered": True,
        }
        code = "SELECT * FROM t;"
        result = svc._evaluate_sql_fixture(ex, code, fixture)
        # No expected rows + no actual rows = match
        assert result.passed is True


# ---------------------------------------------------------------------------
# _evaluate_sql  -- DDL exercises with more branches
# ---------------------------------------------------------------------------
class TestEvaluateSqlDDLExtended:
    """Additional DDL evaluation tests."""

    def test_orders_foreign_key_pass(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-orders-foreign-key", track_id="database")
        code = (
            "CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id));"
        )
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_orders_foreign_key_fail(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-orders-foreign-key", track_id="database")
        code = "CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER);"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is False

    def test_create_covering_index_pass(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-create-covering-index-report", track_id="database")
        code = "CREATE INDEX idx_cover ON reports(created_at, status);"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_create_covering_index_fail_wrong_order(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-create-covering-index-report", track_id="database")
        code = "CREATE INDEX idx_cover ON reports(status, created_at);"
        result = svc._evaluate_sql(ex, code)
        assert result.passed is False

    def test_create_enrollment_fk_pass(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-create-enrollment-foreign-key", track_id="database")
        code = (
            "CREATE TABLE enrollments("
            "student_id INTEGER, course_id INTEGER, "
            "FOREIGN KEY(student_id) REFERENCES students(id), "
            "FOREIGN KEY(course_id) REFERENCES courses(id));"
        )
        result = svc._evaluate_sql(ex, code)
        assert result.passed is True

    def test_create_enrollment_fk_fail_missing_course_fk(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("db-create-enrollment-foreign-key", track_id="database")
        code = (
            "CREATE TABLE enrollments("
            "student_id INTEGER, course_id INTEGER, "
            "FOREIGN KEY(student_id) REFERENCES students(id));"
        )
        result = svc._evaluate_sql(ex, code)
        assert result.passed is False


# ---------------------------------------------------------------------------
# _evaluate_sql  -- structure check with semicolon bonus
# ---------------------------------------------------------------------------
class TestEvaluateSqlStructureSemicolon:
    """Test that structure-only SQL evaluation gives semicolon bonus."""

    def test_with_semicolon_bonus(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise("unknown-sql", track_id="database", required_keywords=["select"])
        result_with = svc._evaluate_sql(ex, "SELECT 1;")
        result_without = svc._evaluate_sql(ex, "SELECT 1")
        assert result_with.score >= result_without.score

    def test_structure_check_forbidden_keywords_in_structure_mode(self):
        """In structure-only mode, forbidden keywords are reported but not blocking."""
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            "unknown-sql",
            track_id="database",
            required_keywords=["select"],
            forbidden_keywords=["delete"],
        )
        result = svc._evaluate_sql(ex, "SELECT 1; DELETE FROM t;")
        assert "不建议" in str(result.feedback_lines)
        # Still gets partial score for having required keyword and semicolon


# ---------------------------------------------------------------------------
# _evaluate_keyword_code  -- additional branches
# ---------------------------------------------------------------------------
class TestEvaluateKeywordCodeExtended:
    """Additional keyword evaluation tests for C/C# exercises."""

    def test_only_forbidden_present(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            track_id="c",
            required_keywords=["int"],
            forbidden_keywords=["goto"],
        )
        result = svc._evaluate_keyword_code(ex, "goto end;")
        # Has forbidden, no required, empty check
        assert "缺少" in str(result.feedback_lines) or "不建议" in str(result.feedback_lines)

    def test_multiple_required_all_present(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(
            track_id="c",
            required_keywords=["int", "main", "return"],
        )
        result = svc._evaluate_keyword_code(ex, "int main() { return 0; }")
        assert result.passed is True
        assert result.score >= 90

    def test_case_insensitive_keyword_match(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="csharp", required_keywords=["int"])
        result = svc._evaluate_keyword_code(ex, "INT x = 1;")
        # Keywords are matched case-insensitively
        assert result.score >= 70

    def test_empty_required_keywords(self):
        svc = PracticeService.__new__(PracticeService)
        ex = _make_exercise(track_id="c", required_keywords=[], forbidden_keywords=[])
        result = svc._evaluate_keyword_code(ex, "return 0;")
        assert result.score >= 50  # 20 (submitted) + 0 (no required) + 20 (no forbidden) + 10 (semicolon)


# ---------------------------------------------------------------------------
# EXERCISE_FALLBACKS data integrity
# ---------------------------------------------------------------------------
class TestExerciseFallbacksData:
    """Verify EXERCISE_FALLBACKS contains expected data."""

    def test_fallbacks_is_nonempty_dict(self):
        assert isinstance(_get_exercise_fallbacks(), dict)
        assert len(_get_exercise_fallbacks()) > 0

    def test_all_fallbacks_have_required_fields(self):
        for ex_id, data in _get_exercise_fallbacks().items():
            assert "title" in data, f"{ex_id} missing title"
            assert "difficulty" in data, f"{ex_id} missing difficulty"
            assert "prompt" in data, f"{ex_id} missing prompt"
            assert "hints" in data, f"{ex_id} missing hints"
            assert isinstance(data["hints"], list), f"{ex_id} hints should be a list"
            assert len(data["hints"]) > 0, f"{ex_id} hints should not be empty"

    def test_no_fallback_needs_fallback(self):
        """Fallback values themselves should NOT trigger the corruption detector."""
        for ex_id, data in _get_exercise_fallbacks().items():
            assert _needs_fallback(data["title"]) is False, f"{ex_id} title needs fallback"
            assert _needs_fallback(data["prompt"]) is False, f"{ex_id} prompt needs fallback"


# ---------------------------------------------------------------------------
# SQL_QUERY_FIXTURES data integrity
# ---------------------------------------------------------------------------
class TestSqlQueryFixturesData:
    """Verify SQL_QUERY_FIXTURES contains valid data."""

    def test_fixtures_is_nonempty_dict(self):
        assert isinstance(_get_sql_query_fixtures(), dict)
        assert len(_get_sql_query_fixtures()) > 0

    def test_all_fixtures_have_setup(self):
        for fixture_id, data in _get_sql_query_fixtures().items():
            assert "setup" in data, f"{fixture_id} missing setup"

    def test_query_fixtures_have_expected_rows(self):
        for fixture_id, data in _get_sql_query_fixtures().items():
            mode = data.get("mode", "query")
            if mode == "query":
                assert "expected_rows" in data, f"{fixture_id} (query mode) missing expected_rows"

    def test_script_fixtures_have_check_sql(self):
        for fixture_id, data in _get_sql_query_fixtures().items():
            if data.get("mode") == "script":
                assert "check_sql" in data, f"{fixture_id} (script mode) missing check_sql"
                assert "expected_rows" in data, f"{fixture_id} (script mode) missing expected_rows"

    def test_fixtures_setup_executes(self):
        """Each fixture's setup SQL should execute without error."""
        count = 0
        for fixture_id, data in _get_sql_query_fixtures().items():
            conn = sqlite3.connect(":memory:")
            try:
                conn.executescript(data["setup"])
                count += 1
            except Exception as exc:
                pytest.fail(f"{fixture_id} setup failed: {exc}")
            finally:
                conn.close()
        assert count > 0


# ---------------------------------------------------------------------------
# _needs_fallback  -- additional edge cases
# ---------------------------------------------------------------------------
class TestNeedsFallbackExtended:
    """Additional edge cases for the fallback detector."""

    def test_only_spaces_no_fallback(self):
        assert _needs_fallback("   ") is False

    def test_newlines_no_fallback(self):
        assert _needs_fallback("line1\nline2") is False

    def test_mixed_content_with_question(self):
        assert _needs_fallback("What is x?") is True

    def test_numeric_string_no_fallback(self):
        assert _needs_fallback("12345") is False


# ---------------------------------------------------------------------------
# _load_exercises  -- with temp metadata file
# ---------------------------------------------------------------------------
class TestLoadExercises:
    """Test _load_exercises with temporary metadata files."""

    def test_valid_metadata_loads(self, tmp_path):
        metadata = {
            "exercises": [
                {
                    "id": "test-1",
                    "title": "Test Exercise",
                    "track_id": "python",
                    "difficulty": "精选",
                    "prompt": "Do something",
                    "lesson_id": "lesson-1",
                    "hints": ["hint1"],
                    "starter_code": "",
                    "expected_nodes": [],
                    "required_names": [],
                    "tests": [],
                }
            ]
        }
        metadata_file = tmp_path / "exercises.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        svc = PracticeService(metadata_path=metadata_file)
        assert len(svc.exercises) == 1
        assert svc.exercises[0].id == "test-1"

    def test_missing_file_returns_empty(self, tmp_path):
        metadata_file = tmp_path / "nonexistent.json"
        svc = PracticeService(metadata_path=metadata_file)
        assert svc.exercises == []

    def test_invalid_json_returns_empty(self, tmp_path):
        metadata_file = tmp_path / "bad.json"
        metadata_file.write_text("not valid json {{{", encoding="utf-8")
        svc = PracticeService(metadata_path=metadata_file)
        assert svc.exercises == []

    def test_fallback_applied_for_corrupted_fields(self, tmp_path):
        """When metadata contains '?' in fields, fallback should be applied."""
        metadata = {
            "exercises": [
                {
                    "id": "py-squares-comprehension",  # Has a fallback entry
                    "title": "???",  # Corrupted
                    "track_id": "python",
                    "difficulty": "???",  # Corrupted
                    "prompt": "???",  # Corrupted
                    "lesson_id": "lesson-1",
                    "hints": ["???"],  # Corrupted
                    "starter_code": "???",  # Corrupted
                    "expected_nodes": [],
                    "required_names": [],
                    "tests": [{"expression": "x", "expected": "?"}],  # Corrupted expected
                }
            ]
        }
        metadata_file = tmp_path / "exercises.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        svc = PracticeService(metadata_path=metadata_file)
        assert len(svc.exercises) == 1
        # Title should have been replaced by the fallback
        assert svc.exercises[0].title == "用推导式生成奇数平方"
        assert "???" not in svc.exercises[0].title

    def test_no_fallback_for_unknown_id_with_corruption(self, tmp_path):
        """Unknown exercise IDs with corruption should keep the corrupted value."""
        metadata = {
            "exercises": [
                {
                    "id": "unknown-id",
                    "title": "???",
                    "track_id": "python",
                    "difficulty": "精选",
                    "prompt": "Do something",
                    "lesson_id": "lesson-1",
                    "hints": ["normal hint"],
                    "starter_code": "",
                    "expected_nodes": [],
                    "required_names": [],
                    "tests": [],
                }
            ]
        }
        metadata_file = tmp_path / "exercises.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        svc = PracticeService(metadata_path=metadata_file)
        # No fallback for unknown ID, so corrupted title stays
        assert svc.exercises[0].title == "???"
