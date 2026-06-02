"""Tests for app.database -- CRUD operations, pure helpers, and migration logic.

Uses a temporary SQLite database so tests are fully isolated and require
no GUI, network, or credential-manager access.
"""

import pytest

from app.database import AppDatabase, close_connection


@pytest.fixture()
def db(tmp_path):
    """Create an AppDatabase backed by a temporary file, and clean up after."""
    # Close any stale global connection left by a previous test so that
    # get_connection() opens a fresh one pointing at our temp database.
    close_connection()
    db_path = tmp_path / "test.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    # Clear any data migrated from the legacy database so each test
    # starts with a clean slate.
    database.reset_learning_progress()
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# Pure / static helpers
# ---------------------------------------------------------------------------
class TestClipPreview:
    """AppDatabase._clip_preview -- text truncation helper."""

    def test_short_text_unchanged(self):
        assert AppDatabase._clip_preview("hello") == "hello"

    def test_long_text_truncated(self):
        long = "x" * 100
        result = AppDatabase._clip_preview(long, limit=20)
        assert len(result) == 20
        assert result.endswith("…")  # ellipsis

    def test_whitespace_normalized(self):
        assert AppDatabase._clip_preview("  hello   world  ") == "hello world"

    def test_empty_string(self):
        assert AppDatabase._clip_preview("") == ""

    def test_none_input(self):
        assert AppDatabase._clip_preview(None) == ""


class TestLooksLikeCorruptedMessage:
    """AppDatabase._looks_like_corrupted_message -- corruption detector."""

    def test_normal_message_not_corrupted(self):
        assert AppDatabase._looks_like_corrupted_message("这是一条正常的中文消息") is False

    def test_empty_string_not_corrupted(self):
        assert AppDatabase._looks_like_corrupted_message("") is False

    def test_placeholder_not_corrupted(self):
        assert AppDatabase._looks_like_corrupted_message(
            "旧消息因早期编码问题已自动清理"
        ) is False

    def test_garbled_high_question_ratio_detected(self):
        # Many question marks, no Chinese characters, compact length > 6
        garbled = "??????????????????"
        assert AppDatabase._looks_like_corrupted_message(garbled) is True

    def test_chinese_with_questions_not_corrupted(self):
        # Has Chinese chars -> should NOT be flagged
        assert AppDatabase._looks_like_corrupted_message("你好??????") is False


# ---------------------------------------------------------------------------
# Database CRUD
# ---------------------------------------------------------------------------
class TestLessonProgress:
    """Lesson progress tracking: open, complete, status."""

    def test_initial_status_not_started(self, db):
        assert db.lesson_status("lesson-1") == "not_started"

    def test_mark_opened_sets_in_progress(self, db):
        db.mark_lesson_opened("lesson-1", "track-py")
        assert db.lesson_status("lesson-1") == "in_progress"

    def test_mark_completed(self, db):
        db.mark_lesson_completed("lesson-1", "track-py")
        assert db.lesson_status("lesson-1") == "completed"

    def test_mark_opened_after_completed_stays_completed(self, db):
        db.mark_lesson_completed("lesson-1", "track-py")
        db.mark_lesson_opened("lesson-1", "track-py")
        assert db.lesson_status("lesson-1") == "completed"

    def test_completed_lessons_count(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.mark_lesson_completed("l2", "t1")
        assert db.completed_lessons() == 2

    def test_track_completion(self, db):
        db.mark_lesson_completed("l1", "track-py")
        db.mark_lesson_completed("l2", "track-py")
        db.mark_lesson_completed("l3", "track-c")
        assert db.track_completion("track-py") == 2
        assert db.track_completion("track-c") == 1


class TestNotes:
    """Lesson notes CRUD."""

    def test_load_empty_note(self, db):
        assert db.load_note("lesson-1") == ""

    def test_save_and_load_note(self, db):
        db.save_note("lesson-1", "my notes")
        assert db.load_note("lesson-1") == "my notes"

    def test_overwrite_note(self, db):
        db.save_note("lesson-1", "v1")
        db.save_note("lesson-1", "v2")
        assert db.load_note("lesson-1") == "v2"


class TestPracticeAttempts:
    """Practice attempt recording and retrieval."""

    def test_record_and_recent(self, db):
        db.record_attempt(
            exercise_id="ex-1",
            exercise_title_snapshot="Title",
            track_id="t1",
            code_snapshot="print(1)",
            score=80,
            passed=True,
            duration_sec=5,
            feedback="ok",
        )
        attempts = db.recent_attempts(limit=5)
        assert len(attempts) == 1
        assert attempts[0][2] == 80  # score
        assert attempts[0][3] == 1  # passed

    def test_average_score_empty(self, db):
        assert db.average_score() == 0

    def test_average_score(self, db):
        for score in (60, 80, 100):
            db.record_attempt("ex", "T", "t1", "", score, True, 1, "")
        assert db.average_score() == 80


class TestExerciseDrafts:
    """Exercise draft save / load / clear."""

    def test_load_nonexistent_draft(self, db):
        assert db.load_exercise_draft("ex-1") is None

    def test_save_and_load_draft(self, db):
        db.save_exercise_draft("ex-1", "Title", "print(1)")
        result = db.load_exercise_draft("ex-1")
        assert result is not None
        assert result[0] == "Title"
        assert result[1] == "print(1)"

    def test_clear_draft(self, db):
        db.save_exercise_draft("ex-1", "Title", "print(1)")
        db.clear_exercise_draft("ex-1")
        assert db.load_exercise_draft("ex-1") is None


class TestMentorSessions:
    """Mentor session lifecycle."""

    def test_create_and_list(self, db):
        sid = db.create_mentor_session("Test Session")
        sessions = db.list_mentor_sessions()
        assert any(s[0] == sid for s in sessions)

    def test_rename_session(self, db):
        sid = db.create_mentor_session("Old")
        db.rename_mentor_session(sid, "New")
        sessions = db.list_mentor_sessions()
        matched = [s for s in sessions if s[0] == sid]
        assert matched[0][1] == "New"

    def test_append_and_load_messages(self, db):
        sid = db.create_mentor_session("Chat")
        db.append_mentor_message(sid, "user", "hello")
        db.append_mentor_message(sid, "assistant", "hi there")
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 2
        assert messages[0][0] == "user"
        assert messages[1][0] == "assistant"

    def test_delete_session(self, db):
        sid = db.create_mentor_session("ToDelete")
        db.delete_mentor_session(sid)
        sessions = db.list_mentor_sessions()
        assert not any(s[0] == sid for s in sessions)


class TestResetLearningProgress:
    """reset_learning_progress clears all user data."""

    def test_reset_clears_lessons(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.reset_learning_progress()
        assert db.lesson_status("l1") == "not_started"

    def test_reset_clears_attempts(self, db):
        db.record_attempt("ex", "T", "t1", "", 90, True, 1, "")
        db.reset_learning_progress()
        assert db.recent_attempts() == []


# ---------------------------------------------------------------------------
# Knowledge files
# ---------------------------------------------------------------------------
class TestKnowledgeFiles:
    """Knowledge file CRUD."""

    def test_add_and_list(self, db):
        db.add_knowledge_file("README", "/path/readme", "excerpt text")
        files = db.list_knowledge_files()
        assert len(files) == 1
        assert files[0][1] == "README"

    def test_remove_file(self, db):
        db.add_knowledge_file("README", "/path/readme", "excerpt")
        file_id = db.list_knowledge_files()[0][0]
        db.remove_knowledge_file(file_id)
        assert db.list_knowledge_files() == []
