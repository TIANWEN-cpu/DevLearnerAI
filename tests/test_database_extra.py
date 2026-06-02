"""Additional tests for app.database -- covering remaining branches.

Targets:
- get_connection: reuse existing connection, closed connection recovery (lines 24-29)
- _migrate_legacy_api_key_if_needed (lines 204-223)
- load_api_config: with key_alias, without key_alias, no row (lines 451-459)
- save_api_config: with and without api_key (lines 433-449)
- active_days_streak: gap in days breaks streak (lines 396-424)
- _looks_like_corrupted_message: edge cases (lines 514-531)
- load_mentor_workspace_flags: no-row default (line 645)
- delete_mentor_session: when deleted session is not active (line 568-580)
- mentor_session_snapshot: long content preview (line 477-511)
- recent_attempts: empty result, display_title COALESCE (line 352-366)
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.database import AppDatabase, close_connection, get_connection, now_text


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
# get_connection  -- reuse and recovery
# ---------------------------------------------------------------------------
class TestGetConnection:
    """Test connection management."""

    def test_reuse_existing_connection(self, tmp_path):
        """Calling get_connection twice with same path returns same connection."""
        close_connection()
        db_path = tmp_path / "test.db"
        # Create the file first
        db_path.touch()
        conn1 = get_connection(str(db_path))
        conn2 = get_connection(str(db_path))
        assert conn1 is conn2
        close_connection()

    def test_closed_connection_recovered(self, tmp_path):
        """If the global connection is closed, get_connection creates a new one."""
        close_connection()
        db_path = tmp_path / "test.db"
        db_path.touch()
        conn1 = get_connection(str(db_path))
        # Manually close the connection to simulate corruption
        conn1.close()
        # Next call should detect the closed connection and create a new one
        conn2 = get_connection(str(db_path))
        assert conn2 is not None
        # Verify the new connection works
        conn2.execute("SELECT 1")
        close_connection()


# ---------------------------------------------------------------------------
# save_api_config and load_api_config
# ---------------------------------------------------------------------------
class TestApiConfig:
    """Test API config save/load paths."""

    def test_save_and_load_api_config_with_key(self, db):
        """Save config with api_key and load it back."""
        with (
            patch("app.database.save_secret"),
            patch("app.database.load_secret", return_value="test-key"),
        ):
            db.save_api_config("http://localhost", "test-key", "gpt-4")
            result = db.load_api_config()
            assert result[0] == "http://localhost"
            assert result[1] == "test-key"
            assert result[2] == "gpt-4"

    def test_save_api_config_without_key(self, db):
        """Save config with empty api_key should still save host and model."""
        with patch("app.database.save_secret") as mock_save:
            db.save_api_config("http://localhost", "", "gpt-4")
            # save_secret should NOT have been called
            mock_save.assert_not_called()

    def test_load_api_config_no_row(self, db):
        """Loading config when none exists returns empty strings."""
        result = db.load_api_config()
        assert result == ("", "", "")

    def test_load_api_config_with_legacy_key(self, db):
        """When key_alias is empty, falls back to legacy_api_key."""
        # Directly insert a config row with no key_alias
        db.execute(
            """
            INSERT INTO mentor_api_config (id, host, api_key, model, key_alias)
            VALUES (1, 'http://test', 'legacy-key', 'model-v1', '')
            """
        )
        result = db.load_api_config()
        assert result[0] == "http://test"
        assert result[1] == "legacy-key"
        assert result[2] == "model-v1"


# ---------------------------------------------------------------------------
# active_days_streak  -- gap breaks streak
# ---------------------------------------------------------------------------
class TestActiveDaysStreakExtended:
    """Test streak calculation with gaps."""

    def test_gap_breaks_streak(self, db):
        """Activity today + 3 days ago (gap) should give streak of 1."""
        today = date.today()
        three_days_ago = today - timedelta(days=3)

        # Activity today
        db.mark_lesson_completed("l1", "t1")

        # Activity 3 days ago (not yesterday or day before)
        db.execute(
            """
            INSERT INTO practice_attempts (
                exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                score, passed, duration_sec, submitted_at, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ex", "T", "t1", "", 80, 1, 1, f"{three_days_ago} 12:00:00", "ok"),
        )
        streak = db.active_days_streak()
        assert streak == 1  # Gap breaks the streak

    def test_no_activity_today_streak_zero(self, db):
        """If most recent activity is not today, streak should be 0."""
        yesterday = date.today() - timedelta(days=1)
        db.execute(
            """
            INSERT INTO practice_attempts (
                exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                score, passed, duration_sec, submitted_at, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ex", "T", "t1", "", 80, 1, 1, f"{yesterday} 12:00:00", "ok"),
        )
        assert db.active_days_streak() == 0


# ---------------------------------------------------------------------------
# _looks_like_corrupted_message  -- additional edge cases
# ---------------------------------------------------------------------------
class TestCorruptedMessageExtended:
    """Additional edge cases for the corruption detector."""

    def test_short_string_not_corrupted(self):
        """Short strings (compact < 6 chars) are not flagged even with ?."""
        assert AppDatabase._looks_like_corrupted_message("a?b?") is False

    def test_exactly_6_compact_chars_with_questions(self):
        """6 compact chars with enough ? marks to hit threshold."""
        # "a???b?" -> compact = "a???b?" (6 chars), question count = 4, ratio = 4/6 = 0.67 >= 0.3
        # No Chinese chars -> should be flagged
        assert AppDatabase._looks_like_corrupted_message("a???b?") is True

    def test_none_input_not_corrupted(self):
        assert AppDatabase._looks_like_corrupted_message(None) is False

    def test_whitespace_only_not_corrupted(self):
        assert AppDatabase._looks_like_corrupted_message("   ") is False

    def test_below_question_ratio_not_corrupted(self):
        """If question ratio < 0.3, should not be flagged."""
        # "abcdefgh??" -> compact = "abcdefgh??" (10 chars), question count = 2, ratio = 0.2 < 0.3
        assert AppDatabase._looks_like_corrupted_message("abcdefgh??") is False


# ---------------------------------------------------------------------------
# load_mentor_workspace_flags  -- no row fallback
# ---------------------------------------------------------------------------
class TestWorkspaceFlagsNoRow:
    """Test workspace flags when the row doesn't exist."""

    def test_no_row_returns_defaults(self, db):
        """Delete the workspace state row and verify defaults."""
        db.execute("DELETE FROM mentor_workspace_state WHERE id = 1")
        flags = db.load_mentor_workspace_flags()
        assert flags == {"use_base": True, "use_personal": True, "use_custom": True}


# ---------------------------------------------------------------------------
# delete_mentor_session  -- when deleted is not active
# ---------------------------------------------------------------------------
class TestDeleteMentorSessionExtended:
    """Test deleting sessions that are not the active one."""

    def test_delete_non_active_session_keeps_active(self, db):
        """Deleting a non-active session should not change the active session."""
        sid1 = db.create_mentor_session("Active")
        sid2 = db.create_mentor_session("Other")
        db.set_active_mentor_session(sid1)
        db.delete_mentor_session(sid2)
        assert db.load_active_mentor_session_id() == sid1

    def test_delete_last_session_sets_active_none(self, db):
        """Deleting the only session sets active to None."""
        # Remove all existing sessions first (init_db creates a default)
        for s in db.list_mentor_sessions():
            db.delete_mentor_session(s[0])
        assert db.load_active_mentor_session_id() is None


# ---------------------------------------------------------------------------
# mentor_session_snapshot  -- long content preview
# ---------------------------------------------------------------------------
class TestMentorSessionSnapshotExtended:
    """Test session snapshot with long content."""

    def test_long_content_truncated_in_preview(self, db):
        """Very long message content should be truncated in the preview."""
        sid = db.create_mentor_session("Long")
        long_text = "A" * 200
        db.append_mentor_message(sid, "assistant", long_text)
        snapshot = db.mentor_session_snapshot(sid)
        # Preview should be truncated with ellipsis
        assert len(snapshot["preview"]) < 200
        assert snapshot["preview"].startswith("AI：")

    def test_user_message_preview(self, db):
        """Last message from user should show user prefix."""
        sid = db.create_mentor_session("UserMsg")
        db.append_mentor_message(sid, "user", "What is Python?")
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["preview"].startswith("你：")
        assert "What is Python?" in snapshot["preview"]


# ---------------------------------------------------------------------------
# recent_attempts  -- edge cases
# ---------------------------------------------------------------------------
class TestRecentAttemptsExtended:
    """Test recent_attempts edge cases."""

    def test_empty_result(self, db):
        assert db.recent_attempts() == []

    def test_display_title_coalesce(self, db):
        """When exercise_title_snapshot is empty, uses exercise_id."""
        db.record_attempt("ex-id", "", "t1", "", 50, False, 1, "")
        attempts = db.recent_attempts()
        assert len(attempts) == 1
        assert attempts[0][1] == "ex-id"  # COALESCE falls back to exercise_id

    def test_display_title_snapshot_used(self, db):
        """When exercise_title_snapshot is set, it's used as display_title."""
        db.record_attempt("ex-id", "My Title", "t1", "", 50, False, 1, "")
        attempts = db.recent_attempts()
        assert len(attempts) == 1
        assert attempts[0][1] == "My Title"

    def test_display_title_null_snapshot_uses_id(self, db):
        """When exercise_title_snapshot is NULL, exercise_id is used."""
        db.execute(
            """
            INSERT INTO practice_attempts (
                exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                score, passed, duration_sec, submitted_at, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("my-exercise", None, "t1", "", 70, 1, 1, now_text(), "ok"),
        )
        attempts = db.recent_attempts()
        assert attempts[0][1] == "my-exercise"


# ---------------------------------------------------------------------------
# _migrate_legacy_db_if_needed
# ---------------------------------------------------------------------------
class TestMigrateLegacyDb:
    """Test legacy DB migration logic."""

    def test_no_migration_when_db_exists(self, tmp_path):
        """If the target DB already exists, no migration happens."""
        close_connection()
        db_path = tmp_path / "test.db"
        db_path.write_text("existing", encoding="utf-8")
        AppDatabase(db_path=db_path)
        # Should not raise or try to migrate
        assert db_path.exists()
        close_connection()

    def test_init_db_is_idempotent(self, db):
        """Calling init_db twice should not fail."""
        db.init_db()
        db.init_db()
        # Should still work
        assert db.lesson_status("any") == "not_started"
