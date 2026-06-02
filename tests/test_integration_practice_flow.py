"""Integration tests for the practice flow: exercise loading -> submission -> evaluation -> scoring.

These tests exercise the full PracticeService pipeline using real metadata
files, the evaluator dispatch, and database recording of attempts.
"""

import pytest

from app.database import AppDatabase, close_connection
from app.practice.models import EvaluationResult, Exercise
from app.practice.normalizer import normalize_rows
from app.practice_service import PracticeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def practice_service():
    """Create a PracticeService backed by real exercises.json metadata."""
    return PracticeService()


@pytest.fixture()
def db(tmp_path):
    """Create an isolated AppDatabase for each test."""
    close_connection()
    db_path = tmp_path / "practice_flow.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# 1. Exercise loading and structure validation
# ---------------------------------------------------------------------------
class TestExerciseLoading:
    """Verify that exercises load from real metadata files."""

    def test_exercises_load_from_metadata(self, practice_service):
        assert len(practice_service.exercises) > 0, "Should load exercises from exercises.json"

    def test_exercises_have_required_fields(self, practice_service):
        for ex in practice_service.exercises:
            assert isinstance(ex, Exercise)
            assert ex.id, "Exercise must have an id"
            assert ex.title, f"Exercise {ex.id} must have a title"
            assert ex.track_id, f"Exercise {ex.id} must have a track_id"
            assert ex.difficulty, f"Exercise {ex.id} must have a difficulty"

    def test_exercise_by_id(self, practice_service):
        first = practice_service.exercises[0]
        found = practice_service.exercise_by_id(first.id)
        assert found is not None
        assert found.id == first.id
        assert found.title == first.title

    def test_exercise_by_id_not_found(self, practice_service):
        assert practice_service.exercise_by_id("nonexistent-99999") is None

    def test_filter_by_track(self, practice_service):
        all_tracks = {ex.track_id for ex in practice_service.exercises}
        assert all_tracks, "Should have at least one track"
        sample_track = next(iter(all_tracks))
        filtered = practice_service.filtered(sample_track, "all")
        assert len(filtered) > 0
        for ex in filtered:
            assert ex.track_id == sample_track

    def test_filter_by_difficulty(self, practice_service):
        all_diffs = {ex.difficulty for ex in practice_service.exercises}
        assert all_diffs
        sample_diff = next(iter(all_diffs))
        filtered = practice_service.filtered("all", sample_diff)
        assert len(filtered) > 0
        for ex in filtered:
            assert ex.difficulty == sample_diff

    def test_filter_combined(self, practice_service):
        all_tracks = {ex.track_id for ex in practice_service.exercises}
        sample_track = next(iter(all_tracks))
        track_exercises = [ex for ex in practice_service.exercises if ex.track_id == sample_track]
        if not track_exercises:
            pytest.skip("No exercises for sample track")
        sample_diff = track_exercises[0].difficulty
        filtered = practice_service.filtered(sample_track, sample_diff)
        for ex in filtered:
            assert ex.track_id == sample_track
            assert ex.difficulty == sample_diff


# ---------------------------------------------------------------------------
# 2. SQL exercises with actual schema validation
# ---------------------------------------------------------------------------
class TestSQLExerciseEvaluation:
    """Test SQL exercise evaluation using the real evaluator and fixtures."""

    def _find_sql_exercise(self, practice_service, exercise_id):
        ex = practice_service.exercise_by_id(exercise_id)
        if ex is None:
            pytest.skip(f"SQL exercise '{exercise_id}' not found in metadata")
        return ex

    def test_select_active_users(self, practice_service):
        """Evaluate a real SQL SELECT exercise against fixtures."""
        ex = self._find_sql_exercise(practice_service, "db-select-active")
        code = "SELECT name FROM users WHERE status = 'active';"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70
        assert result.passed is True

    def test_order_count(self, practice_service):
        """Evaluate a GROUP BY + COUNT exercise."""
        ex = self._find_sql_exercise(practice_service, "db-order-count")
        code = "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id ORDER BY user_id;"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70

    def test_join_user_order(self, practice_service):
        """Evaluate a JOIN exercise."""
        ex = self._find_sql_exercise(practice_service, "db-join-user-order")
        code = "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id;"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70

    def test_subquery_high_score(self, practice_service):
        """Evaluate a subquery exercise."""
        ex = self._find_sql_exercise(practice_service, "db-subquery-high-score")
        code = "SELECT student FROM scores WHERE score > (SELECT AVG(score) FROM scores);"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70

    def test_empty_sql_submission_fails(self, practice_service):
        """Empty SQL code should produce a failing result."""
        exercises = practice_service.filtered("database", "all")
        if not exercises:
            pytest.skip("No database exercises found")
        ex = exercises[0]
        result = practice_service.evaluate(ex, "")
        assert result.passed is False
        assert result.score < 70

    def test_sql_missing_required_keywords_penalized(self, practice_service):
        """Missing required keywords should reduce the score."""
        exercises = practice_service.filtered("database", "all")
        if not exercises:
            pytest.skip("No database exercises found")
        # Find an exercise with required keywords
        ex_with_kw = next((e for e in exercises if e.required_keywords), None)
        if not ex_with_kw:
            pytest.skip("No database exercise with required keywords")
        # Submit something that deliberately avoids required keywords
        result = practice_service.evaluate(ex_with_kw, "SELECT 1;")
        # Score should be lower than perfect since keywords are missing
        assert isinstance(result, EvaluationResult)
        assert result.score < 100

    def test_ddl_exercise_enrollment_table(self, practice_service):
        """Test DDL exercise that validates schema changes."""
        ex = self._find_sql_exercise(practice_service, "db-design-enrollment-table")
        code = """
            CREATE TABLE enrollments (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrolled_at TEXT
            );
        """
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70

    def test_ddl_exercise_create_index(self, practice_service):
        """Test index creation DDL exercise."""
        ex = self._find_sql_exercise(practice_service, "db-create-index-users-email")
        code = "CREATE INDEX idx_users_email ON users(email);"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70

    def test_ddl_exercise_add_column(self, practice_service):
        """Test ALTER TABLE ADD COLUMN exercise."""
        ex = self._find_sql_exercise(practice_service, "db-add-column-migration")
        code = "ALTER TABLE users ADD COLUMN last_login TEXT;"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score >= 70


# ---------------------------------------------------------------------------
# 3. Python exercises with sandbox execution
# ---------------------------------------------------------------------------
class TestPythonExerciseEvaluation:
    """Test Python exercise evaluation through the sandbox."""

    def _find_python_exercise(self, practice_service, exercise_id):
        ex = practice_service.exercise_by_id(exercise_id)
        if ex is None:
            pytest.skip(f"Python exercise '{exercise_id}' not found in metadata")
        return ex

    def test_py_add_function(self, practice_service):
        """Evaluate a simple function exercise."""
        ex = self._find_python_exercise(practice_service, "py-add")
        code = "def add(a, b):\n    return a + b\n"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.passed is True
        assert result.score >= 70
        assert "语法检查通过" in " ".join(result.feedback_lines)

    def test_py_normalize_name(self, practice_service):
        """Evaluate string manipulation exercise."""
        ex = self._find_python_exercise(practice_service, "py-normalize-name")
        code = "def normalize_name(text):\n    return text.strip().capitalize()\n"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.passed is True
        assert result.score >= 70

    def test_py_syntax_error_fails(self, practice_service):
        """Syntax errors should produce a failing result with score 0."""
        exercises = practice_service.filtered("python", "all")
        if not exercises:
            pytest.skip("No python exercises found")
        ex = exercises[0]
        code = "def broken(\n  this is not valid python"
        result = practice_service.evaluate(ex, code)
        assert result.passed is False
        assert result.score == 0
        assert any("语法错误" in line for line in result.feedback_lines)

    def test_py_incomplete_structure_penalized(self, practice_service):
        """Missing expected AST nodes should penalize the score."""
        ex = self._find_python_exercise(practice_service, "py-add")
        # Define function without return -- missing Return node
        code = "def add(a, b):\n    pass\n"
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score < 100, "Missing Return should reduce score"

    def test_py_empty_code_fails(self, practice_service):
        exercises = practice_service.filtered("python", "all")
        if not exercises:
            pytest.skip("No python exercises found")
        result = practice_service.evaluate(exercises[0], "")
        assert result.passed is False


# ---------------------------------------------------------------------------
# 4. C/C# keyword exercises
# ---------------------------------------------------------------------------
class TestKeywordExerciseEvaluation:
    """Test keyword-based evaluation for C/C# exercises."""

    def test_csharp_exercise_dispatched(self, practice_service):
        """C# exercises should be evaluated via keyword checker."""
        csharp_exercises = practice_service.filtered("csharp", "all")
        if not csharp_exercises:
            pytest.skip("No csharp exercises in metadata")
        ex = csharp_exercises[0]
        # Build code that includes some of the required keywords
        code_parts = []
        for kw in ex.required_keywords[:3]:
            code_parts.append(f"// {kw}")
        code_parts.append(";")
        code_parts.append("{")
        code = "\n".join(code_parts)
        result = practice_service.evaluate(ex, code)
        assert isinstance(result, EvaluationResult)
        assert result.score > 0

    def test_c_exercise_dispatched(self, practice_service):
        c_exercises = practice_service.filtered("c", "all")
        if not c_exercises:
            pytest.skip("No c exercises in metadata")
        ex = c_exercises[0]
        result = practice_service.evaluate(ex, "int main() { return 0; }")
        assert isinstance(result, EvaluationResult)


# ---------------------------------------------------------------------------
# 5. Evaluation + Database recording integration
# ---------------------------------------------------------------------------
class TestEvaluationRecordingIntegration:
    """Test the full flow: load exercise -> evaluate -> record in database."""

    def test_evaluate_and_record_python(self, practice_service, db):
        """Evaluate a Python exercise and record the result in the database."""
        ex = practice_service.exercise_by_id("py-add")
        if ex is None:
            pytest.skip("py-add exercise not found")
        code = "def add(a, b):\n    return a + b\n"
        result = practice_service.evaluate(ex, code)

        # Record the attempt
        db.record_attempt(
            exercise_id=ex.id,
            exercise_title_snapshot=ex.title,
            track_id=ex.track_id,
            code_snapshot=code,
            score=result.score,
            passed=result.passed,
            duration_sec=result.duration_sec,
            feedback=result.feedback_text,
        )

        # Verify it was recorded
        attempts = db.recent_attempts(limit=5)
        assert len(attempts) == 1
        assert attempts[0][2] == result.score  # score
        assert attempts[0][3] == (1 if result.passed else 0)  # passed

    def test_evaluate_and_record_sql(self, practice_service, db):
        """Evaluate a SQL exercise and record the result."""
        ex = practice_service.exercise_by_id("db-select-active")
        if ex is None:
            pytest.skip("db-select-active exercise not found")
        code = "SELECT name FROM users WHERE status = 'active';"
        result = practice_service.evaluate(ex, code)

        db.record_attempt(
            exercise_id=ex.id,
            exercise_title_snapshot=ex.title,
            track_id=ex.track_id,
            code_snapshot=code,
            score=result.score,
            passed=result.passed,
            duration_sec=result.duration_sec,
            feedback=result.feedback_text,
        )

        attempts = db.recent_attempts(limit=5)
        assert len(attempts) == 1
        assert attempts[0][2] >= 70

    def test_multiple_attempts_average_score(self, practice_service, db):
        """Multiple attempts should be reflected in the average score."""
        ex = practice_service.exercise_by_id("py-add")
        if ex is None:
            pytest.skip("py-add exercise not found")

        scores = []
        code = "def add(a, b):\n    return a + b\n"
        for _ in range(3):
            result = practice_service.evaluate(ex, code)
            scores.append(result.score)
            db.record_attempt(ex.id, ex.title, ex.track_id, code, result.score, result.passed, result.duration_sec, "")

        avg = db.average_score()
        expected_avg = round(sum(scores) / len(scores))
        assert avg == expected_avg

    def test_draft_save_load_submit_flow(self, practice_service, db):
        """Simulate: start exercise -> save draft -> load draft -> submit."""
        ex = practice_service.exercise_by_id("py-add")
        if ex is None:
            pytest.skip("py-add exercise not found")

        # Save a draft
        partial_code = "def add(a, b):\n    pass\n"
        db.save_exercise_draft(ex.id, ex.title, partial_code)

        # Load the draft
        draft = db.load_exercise_draft(ex.id)
        assert draft is not None
        assert draft[0] == ex.title
        assert draft[1] == partial_code

        # Complete and submit
        final_code = "def add(a, b):\n    return a + b\n"
        result = practice_service.evaluate(ex, final_code)
        db.record_attempt(
            ex.id,
            ex.title,
            ex.track_id,
            final_code,
            result.score,
            result.passed,
            result.duration_sec,
            result.feedback_text,
        )

        # Clear the draft
        db.clear_exercise_draft(ex.id)
        assert db.load_exercise_draft(ex.id) is None

        # Verify the attempt was recorded
        assert len(db.recent_attempts()) == 1


# ---------------------------------------------------------------------------
# 6. Normalizer integration
# ---------------------------------------------------------------------------
class TestNormalizerIntegration:
    """Test normalize_rows in the context of SQL evaluation comparison."""

    def test_normalize_handles_mixed_types(self):
        rows = [("Ada", 25, None), ("Ben", 30, "active")]
        result = normalize_rows(rows, ordered=False)
        assert len(result) == 2
        assert all(isinstance(r, tuple) for r in result)

    def test_normalize_preserves_order_when_requested(self):
        rows = [(3, "c"), (1, "a"), (2, "b")]
        result = normalize_rows(rows, ordered=True)
        assert result == [(3, "c"), (1, "a"), (2, "b")]

    def test_normalize_empty(self):
        assert normalize_rows([], ordered=False) == []
        assert normalize_rows([], ordered=True) == []
