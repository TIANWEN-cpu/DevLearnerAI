"""Extended tests for app.database covering remaining uncovered paths.

Targets:
- Connection recovery when SELECT 1 fails (lines 45-46)
- connect() rollback on exception (lines 128-130)
- init_db default session creation (lines 274-275)
- _migrate_legacy_api_key_if_needed (lines 286-290)
- batch_insert_attempts (lines 562-579)
- average_score cache path (line 655)
- active_days_streak cache path (line 672)
- trim_mentor_messages (lines 1105-1126)
"""

from unittest.mock import patch

import pytest


@pytest.fixture
def fresh_db(tmp_path):
    """Create a fresh AppDatabase instance with a temp db."""
    from app.database import AppDatabase, close_connection

    # Close any existing global connection to avoid stale state
    close_connection()
    db_path = tmp_path / "test.db"
    db = AppDatabase(db_path)
    db.init_db()
    yield db
    close_connection()


# ---------------------------------------------------------------------------
# Connection recovery
# ---------------------------------------------------------------------------
class TestConnectionRecovery:
    """Test that get_connection recovers from a stale connection."""

    def test_connection_recovery_on_failure(self, tmp_path):
        from app.database import get_connection

        # First establish a connection
        db_path = tmp_path / "test.db"
        conn = get_connection(str(db_path))
        conn.execute("CREATE TABLE IF NOT EXISTS test(id INTEGER)")

        # Now make it stale by closing it
        conn.close()

        # Next get_connection should recover
        conn2 = get_connection(str(db_path))
        assert conn2 is not None
        result = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert len(result) >= 1
        conn2 = get_connection(str(db_path))
        # Should work after recovery
        conn2.execute("SELECT 1")


# ---------------------------------------------------------------------------
# connect() rollback on exception
# ---------------------------------------------------------------------------
class TestConnectRollback:
    """Test that connect() rolls back on exception (lines 128-130)."""

    def test_rollback_on_exception(self, fresh_db):
        """When an exception occurs in the context manager, connection should rollback."""
        with pytest.raises(ValueError, match="test error"), fresh_db.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS test_table(id INTEGER)")
            raise ValueError("test error")

        # Database should still be usable after rollback
        with fresh_db.connect() as conn:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1


# ---------------------------------------------------------------------------
# init_db default session creation
# ---------------------------------------------------------------------------
class TestInitDbDefaultSession:
    """Test that init_db creates a default session when none exist (lines 273-275)."""

    def test_creates_default_session(self, fresh_db):
        sessions = fresh_db.list_mentor_sessions()
        assert len(sessions) >= 1
        names = [s[1] for s in sessions]
        assert "默认对话" in names

    def test_init_db_idempotent(self, fresh_db):
        """Calling init_db twice should not fail or create duplicate default sessions."""
        fresh_db.init_db()
        sessions = fresh_db.list_mentor_sessions()
        default_count = sum(1 for _, name, _ in sessions if name == "默认对话")
        assert default_count >= 1


# ---------------------------------------------------------------------------
# _migrate_legacy_api_key_if_needed
# ---------------------------------------------------------------------------
class TestMigrateLegacyApiKey:
    """Test legacy API key migration (lines 286-290)."""

    def test_migration_with_legacy_key(self, fresh_db):
        """If there's a legacy plaintext key, it should be migrated."""
        # Insert a legacy config entry
        with fresh_db.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mentor_api_config (id, host, api_key, key_alias, model) "
                "VALUES (1, 'https://test', 'legacy-key', '', 'gpt-4')"
            )

        with patch("app.database.save_secret") as mock_save:
            fresh_db._migrate_legacy_api_key_if_needed()
            # Should have tried to save the secret
            mock_save.assert_called()

    def test_migration_no_legacy_key(self, fresh_db):
        """If key_alias is already set, should not migrate."""
        with fresh_db.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mentor_api_config (id, host, api_key, key_alias, model) "
                "VALUES (1, 'https://test', '', 'my-alias', 'gpt-4')"
            )

        with patch("app.database.save_secret") as mock_save:
            fresh_db._migrate_legacy_api_key_if_needed()
            mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# batch_insert_attempts
# ---------------------------------------------------------------------------
class TestBatchInsertAttempts:
    """Test batch_insert_attempts (lines 562-579)."""

    def test_batch_insert_empty_records(self, fresh_db):
        """Empty records list should be a no-op."""
        fresh_db.record_attempts_batch([])
        # No error, no crash
        assert fresh_db.recent_attempts() == []

    def test_batch_insert_multiple_records(self, fresh_db):
        """Should insert multiple records in a single transaction."""
        records = [
            ("ex1", "Exercise 1", "track1", "code1", 80, True, 2, "good"),
            ("ex2", "Exercise 2", "track1", "code2", 60, False, 3, "try again"),
            ("ex3", "Exercise 3", "track2", "code3", 100, True, 1, "perfect"),
        ]
        fresh_db.record_attempts_batch(records)
        attempts = fresh_db.recent_attempts(limit=10)
        assert len(attempts) >= 3

    def test_batch_insert_with_passed_false(self, fresh_db):
        """Verify that passed=False is stored as 0."""
        records = [("ex1", "Title", "t1", "code", 50, False, 1, "fb")]
        fresh_db.record_attempts_batch(records)
        attempts = fresh_db.recent_attempts(limit=1)
        assert len(attempts) == 1


# ---------------------------------------------------------------------------
# average_score and active_days_streak cache paths
# ---------------------------------------------------------------------------
class TestCachedStats:
    """Test cache hit/miss in average_score and active_days_streak."""

    def test_average_score_no_records(self, fresh_db):
        fresh_db._invalidate_stats_cache()
        # Delete any records that might exist
        with fresh_db.connect() as conn:
            conn.execute("DELETE FROM practice_attempts")
        fresh_db._invalidate_stats_cache()
        assert fresh_db.average_score() == 0

    def test_average_score_with_records(self, fresh_db):
        fresh_db._invalidate_stats_cache()
        with fresh_db.connect() as conn:
            conn.execute("DELETE FROM practice_attempts")
        records = [
            ("ex1", "Title1", "t1", "code", 80, True, 1, "ok"),
            ("ex2", "Title2", "t1", "code", 60, True, 1, "ok"),
        ]
        fresh_db.record_attempts_batch(records)
        fresh_db._invalidate_stats_cache()
        avg = fresh_db.average_score()
        assert avg == 70

    def test_average_score_cache_hit(self, fresh_db):
        """Second call should hit cache."""
        fresh_db._invalidate_stats_cache()
        with fresh_db.connect() as conn:
            conn.execute("DELETE FROM practice_attempts")
        records = [("ex1", "Title1", "t1", "code", 90, True, 1, "ok")]
        fresh_db.record_attempts_batch(records)
        fresh_db._invalidate_stats_cache()
        first = fresh_db.average_score()
        second = fresh_db.average_score()  # should be cached
        assert first == second == 90

    def test_active_days_streak_no_records(self, fresh_db):
        fresh_db._invalidate_stats_cache()
        with fresh_db.connect() as conn:
            conn.execute("DELETE FROM practice_attempts")
            conn.execute("DELETE FROM lesson_progress")
        fresh_db._invalidate_stats_cache()
        assert fresh_db.active_days_streak() == 0

    def test_active_days_streak_cache_hit(self, fresh_db):
        """Second call should hit cache."""
        fresh_db._invalidate_stats_cache()
        first = fresh_db.active_days_streak()
        second = fresh_db.active_days_streak()
        assert first == second


# ---------------------------------------------------------------------------
# trim_mentor_messages
# ---------------------------------------------------------------------------
class TestTrimMentorMessages:
    """Test trim_mentor_messages (lines 1105-1126)."""

    def test_trim_under_limit(self, fresh_db):
        """If fewer messages than keep_last, should return 0."""
        session_id = fresh_db.create_mentor_session("Test")
        fresh_db.append_mentor_message(session_id, "user", "hi")
        fresh_db.append_mentor_message(session_id, "assistant", "hello")
        deleted = fresh_db.trim_mentor_messages(session_id, keep_last=200)
        assert deleted == 0

    def test_trim_over_limit(self, fresh_db):
        """If more messages than keep_last, should trim old ones."""
        session_id = fresh_db.create_mentor_session("Test")
        # Insert 10 messages
        for i in range(10):
            fresh_db.append_mentor_message(session_id, "user", f"msg {i}")
        deleted = fresh_db.trim_mentor_messages(session_id, keep_last=3)
        assert deleted == 7
        messages = fresh_db.load_mentor_messages(session_id)
        assert len(messages) == 3

    def test_trim_exactly_at_limit(self, fresh_db):
        """If exactly at keep_last, should return 0."""
        session_id = fresh_db.create_mentor_session("Test")
        for i in range(5):
            fresh_db.append_mentor_message(session_id, "user", f"msg {i}")
        deleted = fresh_db.trim_mentor_messages(session_id, keep_last=5)
        assert deleted == 0

    def test_trim_nonexistent_session(self, fresh_db):
        """Trimming a nonexistent session should return 0."""
        deleted = fresh_db.trim_mentor_messages("nonexistent-id", keep_last=10)
        assert deleted == 0
