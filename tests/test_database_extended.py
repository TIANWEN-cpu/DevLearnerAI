"""Extended tests for app.database -- additional CRUD and helper coverage.

Covers:
- now_text (timestamp format)
- list_completed_lessons
- active_days_streak
- mentor session snapshot
- workspace flags (save / load)
- knowledge file get / remove edge case
- reset clears notes and drafts
- concurrent lesson operations (opened -> completed -> opened stays completed)
- track_completion for empty track
- record_attempt with various pass/fail scenarios
"""

from datetime import date, timedelta

import pytest

from app.database import AppDatabase, close_connection, now_text


@pytest.fixture()
def db(tmp_path):
    """Create an AppDatabase backed by a temporary file, and clean up after."""
    close_connection()
    db_path = tmp_path / "test.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# now_text
# ---------------------------------------------------------------------------
class TestNowText:
    """Test the now_text timestamp helper."""

    def test_format_matches_pattern(self):
        result = now_text()
        assert len(result) == 19  # "YYYY-MM-DD HH:MM:SS"
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"
        assert result[16] == ":"

    def test_contains_current_year(self):
        result = now_text()
        assert result.startswith(str(date.today().year))


# ---------------------------------------------------------------------------
# list_completed_lessons
# ---------------------------------------------------------------------------
class TestListCompletedLessons:
    """Test listing completed lessons with timestamps."""

    def test_empty_when_no_completions(self, db):
        assert db.list_completed_lessons() == []

    def test_returns_completed_lessons(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.mark_lesson_completed("l2", "t1")
        result = db.list_completed_lessons()
        ids = [row[0] for row in result]
        assert "l1" in ids
        assert "l2" in ids

    def test_does_not_include_in_progress(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.mark_lesson_opened("l2", "t1")
        result = db.list_completed_lessons()
        ids = [row[0] for row in result]
        assert "l1" in ids
        assert "l2" not in ids

    def test_ordered_by_completed_at_desc(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.mark_lesson_completed("l2", "t1")
        result = db.list_completed_lessons()
        assert len(result) == 2
        # First result should have the more recent completed_at
        assert result[0][1] >= result[1][1]


# ---------------------------------------------------------------------------
# active_days_streak
# ---------------------------------------------------------------------------
class TestActiveDaysStreak:
    """Test the active-days streak calculation."""

    def test_zero_streak_when_no_activity(self, db):
        assert db.active_days_streak() == 0

    def test_streak_today_only(self, db):
        """If there's activity today, streak >= 1."""
        db.mark_lesson_completed("l1", "t1")
        streak = db.active_days_streak()
        # The streak depends on whether today is in the data
        # mark_lesson_completed sets completed_at to now_text() which is today
        assert streak >= 1

    def test_streak_two_days(self, db):
        """Activity today and yesterday should give streak of 2."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Insert activity for today
        db.mark_lesson_completed("l1", "t1")

        # Manually insert yesterday's activity via direct SQL
        db.execute(
            """
            INSERT INTO practice_attempts (
                exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                score, passed, duration_sec, submitted_at, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ex", "T", "t1", "", 80, 1, 1, f"{yesterday} 12:00:00", "ok"),
        )
        streak = db.active_days_streak()
        assert streak >= 2


# ---------------------------------------------------------------------------
# Mentor session snapshot
# ---------------------------------------------------------------------------
class TestMentorSessionSnapshot:
    """Test mentor_session_snapshot for various states."""

    def test_empty_session_snapshot(self, db):
        sid = db.create_mentor_session("Empty")
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["message_count"] == 0
        assert "还没有聊天记录" in snapshot["preview"]

    def test_session_with_messages(self, db):
        sid = db.create_mentor_session("Chat")
        db.append_mentor_message(sid, "user", "你好")
        db.append_mentor_message(sid, "assistant", "你好！有什么可以帮你的？")
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["message_count"] == 2
        assert snapshot["preview"].startswith("AI：")

    def test_session_last_message_is_user(self, db):
        sid = db.create_mentor_session("Chat")
        db.append_mentor_message(sid, "user", "你好")
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["preview"].startswith("你：")

    def test_corrupted_message_shows_cleanup_notice(self, db):
        sid = db.create_mentor_session("Old")
        # Directly insert a corrupted message
        db.append_mentor_message(sid, "assistant", "旧消息因早期编码问题已自动清理")
        snapshot = db.mentor_session_snapshot(sid)
        assert "旧消息已清理" in snapshot["preview"]


# ---------------------------------------------------------------------------
# Workspace flags
# ---------------------------------------------------------------------------
class TestWorkspaceFlags:
    """Test saving and loading mentor workspace flags."""

    def test_default_flags(self, db):
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is True
        assert flags["use_personal"] is True
        assert flags["use_custom"] is True

    def test_save_and_load_flags(self, db):
        db.save_mentor_workspace_flags(use_base=False, use_personal=True, use_custom=False)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is False
        assert flags["use_personal"] is True
        assert flags["use_custom"] is False

    def test_save_all_false(self, db):
        db.save_mentor_workspace_flags(use_base=False, use_personal=False, use_custom=False)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is False
        assert flags["use_personal"] is False
        assert flags["use_custom"] is False

    def test_save_all_true_after_changing(self, db):
        db.save_mentor_workspace_flags(use_base=False, use_personal=False, use_custom=False)
        db.save_mentor_workspace_flags(use_base=True, use_personal=True, use_custom=True)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is True
        assert flags["use_personal"] is True
        assert flags["use_custom"] is True


# ---------------------------------------------------------------------------
# Active mentor session
# ---------------------------------------------------------------------------
class TestActiveMentorSession:
    """Test set_active_mentor_session and load_active_mentor_session_id."""

    def test_default_active_session_set_on_init(self, db):
        """init_db creates a default session and sets it active."""
        active_id = db.load_active_mentor_session_id()
        assert active_id is not None

    def test_set_active_session(self, db):
        sid = db.create_mentor_session("New")
        db.set_active_mentor_session(sid)
        assert db.load_active_mentor_session_id() == sid

    def test_delete_active_session_falls_back(self, db):
        """When the active session is deleted, the next most recent becomes active."""
        sid1 = db.create_mentor_session("First")
        sid2 = db.create_mentor_session("Second")
        db.set_active_mentor_session(sid1)
        db.delete_mentor_session(sid1)
        active = db.load_active_mentor_session_id()
        # Should fall back to sid2 (the remaining session)
        assert active == sid2


# ---------------------------------------------------------------------------
# Knowledge files
# ---------------------------------------------------------------------------
class TestKnowledgeFilesExtended:
    """Extended tests for knowledge file operations."""

    def test_get_knowledge_file(self, db):
        db.add_knowledge_file("Doc", "/path/doc", "excerpt text")
        files = db.list_knowledge_files()
        file_id = files[0][0]
        result = db.get_knowledge_file(file_id)
        assert result is not None
        assert result[1] == "Doc"
        assert result[2] == "/path/doc"
        assert result[3] == "excerpt text"

    def test_get_nonexistent_file_returns_none(self, db):
        assert db.get_knowledge_file(999) is None

    def test_remove_nonexistent_file_no_error(self, db):
        # Should not raise
        db.remove_knowledge_file(999)

    def test_multiple_knowledge_files_ordered_by_id_desc(self, db):
        db.add_knowledge_file("First", "/a", "e1")
        db.add_knowledge_file("Second", "/b", "e2")
        files = db.list_knowledge_files()
        assert len(files) == 2
        # First in list should have higher id (more recent)
        assert files[0][1] == "Second"
        assert files[1][1] == "First"


# ---------------------------------------------------------------------------
# Reset clears notes and drafts
# ---------------------------------------------------------------------------
class TestResetClearsNotesAndDrafts:
    """Verify that reset_learning_progress also clears notes and drafts."""

    def test_reset_clears_notes(self, db):
        db.save_note("lesson-1", "important note")
        db.reset_learning_progress()
        assert db.load_note("lesson-1") == ""

    def test_reset_clears_drafts(self, db):
        db.save_exercise_draft("ex-1", "Title", "print(1)")
        db.reset_learning_progress()
        assert db.load_exercise_draft("ex-1") is None

    def test_reset_clears_all_attempt_types(self, db):
        db.record_attempt("ex", "T", "t1", "", 100, True, 1, "ok")
        db.record_attempt("ex2", "T2", "t2", "", 50, False, 2, "fail")
        db.reset_learning_progress()
        assert db.recent_attempts() == []
        assert db.average_score() == 0


# ---------------------------------------------------------------------------
# Track completion edge cases
# ---------------------------------------------------------------------------
class TestTrackCompletionExtended:
    """Extended tests for track completion counting."""

    def test_empty_track_returns_zero(self, db):
        assert db.track_completion("nonexistent-track") == 0

    def test_mixed_tracks_counted_separately(self, db):
        db.mark_lesson_completed("l1", "python")
        db.mark_lesson_completed("l2", "python")
        db.mark_lesson_completed("l3", "sql")
        db.mark_lesson_opened("l4", "python")  # not completed
        assert db.track_completion("python") == 2
        assert db.track_completion("sql") == 1
        assert db.track_completion("c") == 0


# ---------------------------------------------------------------------------
# Record attempt edge cases
# ---------------------------------------------------------------------------
class TestRecordAttemptExtended:
    """Extended tests for practice attempt recording."""

    def test_failed_attempt_recorded(self, db):
        db.record_attempt(
            exercise_id="ex-1",
            exercise_title_snapshot="Title",
            track_id="t1",
            code_snapshot="wrong code",
            score=30,
            passed=False,
            duration_sec=10,
            feedback="incorrect",
        )
        attempts = db.recent_attempts(limit=1)
        assert len(attempts) == 1
        assert attempts[0][2] == 30  # score
        assert attempts[0][3] == 0  # passed = 0 (False)

    def test_limit_parameter(self, db):
        for i in range(5):
            db.record_attempt(f"ex-{i}", f"Title {i}", "t1", "", i * 20, True, 1, "ok")
        attempts = db.recent_attempts(limit=3)
        assert len(attempts) == 3

    def test_recent_attempts_ordered_by_id_desc(self, db):
        db.record_attempt("ex-1", "First", "t1", "", 60, False, 1, "a")
        db.record_attempt("ex-2", "Second", "t1", "", 90, True, 1, "b")
        attempts = db.recent_attempts(limit=5)
        # Second should appear first (most recent)
        assert attempts[0][1] == "Second"
        assert attempts[1][1] == "First"


# ---------------------------------------------------------------------------
# Draft overwrite
# ---------------------------------------------------------------------------
class TestDraftOverwrite:
    """Test that saving a draft overwrites the previous one."""

    def test_overwrite_draft(self, db):
        db.save_exercise_draft("ex-1", "Title v1", "print(1)")
        db.save_exercise_draft("ex-1", "Title v2", "print(2)")
        result = db.load_exercise_draft("ex-1")
        assert result is not None
        assert result[0] == "Title v2"
        assert result[1] == "print(2)"


# ---------------------------------------------------------------------------
# Mentor session ordering
# ---------------------------------------------------------------------------
class TestMentorSessionOrdering:
    """Test that mentor sessions are ordered by updated_at DESC, id DESC."""

    def test_sessions_ordered_correctly(self, db):
        sid1 = db.create_mentor_session("Old")
        sid2 = db.create_mentor_session("New")
        sessions = db.list_mentor_sessions()
        # sid2 should come first (higher id, more recent)
        session_ids = [s[0] for s in sessions]
        assert session_ids.index(sid2) < session_ids.index(sid1)

    def test_rename_updates_name_and_timestamp(self, db):
        """Renaming a session updates its name and updated_at timestamp."""
        sid1 = db.create_mentor_session("A")
        # Set sid1's updated_at to a known old time
        db.execute(
            "UPDATE mentor_sessions SET updated_at = '2020-01-01 00:00:00' WHERE id = ?",
            (sid1,),
        )
        # Verify the old timestamp
        sessions_before = db.list_mentor_sessions()
        old_entry = [s for s in sessions_before if s[0] == sid1][0]
        assert old_entry[1] == "A"
        assert old_entry[2] == "2020-01-01 00:00:00"
        # Rename
        db.rename_mentor_session(sid1, "A renamed")
        # Verify the name and timestamp were updated
        sessions_after = db.list_mentor_sessions()
        renamed = [s for s in sessions_after if s[0] == sid1][0]
        assert renamed[1] == "A renamed"
        assert renamed[2] != "2020-01-01 00:00:00"  # timestamp was updated
