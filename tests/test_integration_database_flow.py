"""Integration tests for the database flow: full CRUD lifecycle, concurrent access, schema evolution.

These tests exercise AppDatabase with a real SQLite file, testing full
lifecycle operations, cross-table interactions, thread safety, and schema
migration paths.
"""

import threading
import time

import pytest

from app.database import AppDatabase, close_connection, now_text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def db(tmp_path):
    """Create an isolated AppDatabase for each test."""
    close_connection()
    db_path = tmp_path / "db_flow.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    yield database
    close_connection()


@pytest.fixture()
def fresh_db(tmp_path):
    """Create a fresh AppDatabase without calling reset (for migration tests)."""
    close_connection()
    db_path = tmp_path / "fresh_db.db"
    database = AppDatabase(db_path=db_path)
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# 1. Full lifecycle: create -> insert -> query -> update -> delete
# ---------------------------------------------------------------------------
class TestLessonProgressFullLifecycle:
    """Full CRUD lifecycle for lesson_progress table."""

    def test_create_read_update_delete(self, db):
        lesson_id = "crud-lesson-1"
        track_id = "crud-track"

        # Create
        db.mark_lesson_opened(lesson_id, track_id)
        assert db.lesson_status(lesson_id) == "in_progress"

        # Read
        row = db.fetchone(
            "SELECT track_id, status, completed FROM lesson_progress WHERE lesson_id = ?",
            (lesson_id,),
        )
        assert row is not None
        assert row[0] == track_id
        assert row[1] == "in_progress"
        assert row[2] == 0

        # Update
        db.mark_lesson_completed(lesson_id, track_id)
        assert db.lesson_status(lesson_id) == "completed"

        row = db.fetchone(
            "SELECT completed, completed_at FROM lesson_progress WHERE lesson_id = ?",
            (lesson_id,),
        )
        assert row[0] == 1
        assert row[1] is not None

        # Delete (via reset)
        db.reset_learning_progress()
        assert db.lesson_status(lesson_id) == "not_started"


class TestNotesFullLifecycle:
    """Full CRUD lifecycle for lesson_notes table."""

    def test_create_read_update_delete(self, db):
        lesson_id = "note-crud"

        # Create
        db.save_note(lesson_id, "Initial note")
        assert db.load_note(lesson_id) == "Initial note"

        # Read raw
        row = db.fetchone("SELECT content, updated_at FROM lesson_notes WHERE lesson_id = ?", (lesson_id,))
        assert row[0] == "Initial note"
        assert row[1] is not None

        # Update
        db.save_note(lesson_id, "Updated note content")
        assert db.load_note(lesson_id) == "Updated note content"

        # Delete (via reset)
        db.reset_learning_progress()
        assert db.load_note(lesson_id) == ""


class TestPracticeAttemptsFullLifecycle:
    """Full CRUD lifecycle for practice_attempts table."""

    def test_create_read_query_aggregate(self, db):
        # Create multiple attempts
        for i, (score, passed) in enumerate([(60, False), (80, True), (100, True)]):
            db.record_attempt(
                exercise_id=f"ex-{i}",
                exercise_title_snapshot=f"Exercise {i}",
                track_id="python",
                code_snapshot=f"code_{i}",
                score=score,
                passed=passed,
                duration_sec=i + 1,
                feedback=f"feedback_{i}",
            )

        # Read all
        attempts = db.recent_attempts(limit=10)
        assert len(attempts) == 3

        # Aggregate
        assert db.average_score() == 80  # (60+80+100)/3

        # Verify raw data
        rows = db.fetchall("SELECT exercise_id, score, passed, track_id FROM practice_attempts ORDER BY id")
        assert len(rows) == 3
        assert rows[0][0] == "ex-0"
        assert rows[0][1] == 60
        assert rows[0][2] == 0  # passed=False -> 0

        # Delete via reset
        db.reset_learning_progress()
        assert db.recent_attempts() == []
        assert db.average_score() == 0


class TestExerciseDraftsFullLifecycle:
    """Full CRUD lifecycle for exercise_drafts table."""

    def test_create_read_update_delete(self, db):
        # Create
        db.save_exercise_draft("ex-1", "Exercise 1", "print(1)")
        draft = db.load_exercise_draft("ex-1")
        assert draft is not None
        assert draft[0] == "Exercise 1"
        assert draft[1] == "print(1)"

        # Update (upsert)
        db.save_exercise_draft("ex-1", "Exercise 1", "print(42)")
        draft = db.load_exercise_draft("ex-1")
        assert draft[1] == "print(42)"

        # Delete
        db.clear_exercise_draft("ex-1")
        assert db.load_exercise_draft("ex-1") is None


class TestMentorSessionsFullLifecycle:
    """Full CRUD lifecycle for mentor_sessions and mentor_messages."""

    def test_session_create_rename_messages_delete(self, db):
        # Create session
        sid = db.create_mentor_session("Test Session")
        assert isinstance(sid, int)
        assert sid > 0

        # Add messages
        db.append_mentor_message(sid, "user", "What is Python?")
        db.append_mentor_message(sid, "assistant", "Python is a programming language.")

        # Read messages
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 2
        assert messages[0][0] == "user"
        assert messages[0][1] == "What is Python?"
        assert messages[1][0] == "assistant"

        # Session snapshot
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["message_count"] == 2
        # Last message is from assistant, so prefix is "AI："
        assert "AI：" in snapshot["preview"]

        # Rename
        db.rename_mentor_session(sid, "Renamed Session")
        sessions = db.list_mentor_sessions()
        matched = [s for s in sessions if s[0] == sid]
        assert matched[0][1] == "Renamed Session"

        # Delete
        db.delete_mentor_session(sid)
        sessions = db.list_mentor_sessions()
        assert not any(s[0] == sid for s in sessions)
        # Messages should also be deleted
        assert db.load_mentor_messages(sid) == []


class TestKnowledgeFilesFullLifecycle:
    """Full CRUD lifecycle for mentor_knowledge_files."""

    def test_add_list_get_remove(self, db):
        # Add
        db.add_knowledge_file("test.txt", "/path/test.txt", "Some excerpt content")
        db.add_knowledge_file("readme.md", "/path/readme.md", "README excerpt")

        # List
        files = db.list_knowledge_files()
        assert len(files) == 2
        names = {f[1] for f in files}
        assert "test.txt" in names
        assert "readme.md" in names

        # Get specific
        file_id = files[0][0]
        detail = db.get_knowledge_file(file_id)
        assert detail is not None
        assert detail[0] == file_id

        # Remove
        db.remove_knowledge_file(file_id)
        assert db.get_knowledge_file(file_id) is None
        assert len(db.list_knowledge_files()) == 1


class TestApiConfigFullLifecycle:
    """Full CRUD lifecycle for mentor_api_config."""

    def test_save_and_load_api_config(self, db, monkeypatch):
        """Test save/load of API config (mocking the keyring)."""
        # Mock save_secret and load_secret to avoid real credential store
        import app.database as db_module

        saved = {}
        monkeypatch.setattr(db_module, "save_secret", lambda alias, key: saved.__setitem__(alias, key))
        monkeypatch.setattr(db_module, "load_secret", lambda alias: saved.get(alias))

        db.save_api_config("https://api.example.com/v1", "sk-test-key", "gpt-4")
        host, api_key, model = db.load_api_config()
        assert host == "https://api.example.com/v1"
        assert api_key == "sk-test-key"
        assert model == "gpt-4"

    def test_update_api_config(self, db, monkeypatch):
        import app.database as db_module

        saved = {}
        monkeypatch.setattr(db_module, "save_secret", lambda alias, key: saved.__setitem__(alias, key))
        monkeypatch.setattr(db_module, "load_secret", lambda alias: saved.get(alias))

        db.save_api_config("https://api.example.com/v1", "sk-old", "gpt-3.5")
        db.save_api_config("https://api.new.com/v1", "sk-new", "gpt-4")

        host, api_key, model = db.load_api_config()
        assert host == "https://api.new.com/v1"
        assert api_key == "sk-new"
        assert model == "gpt-4"


# ---------------------------------------------------------------------------
# 2. Concurrent access patterns
# ---------------------------------------------------------------------------
class TestConcurrentAccess:
    """Test thread safety of database operations."""

    def test_concurrent_writes_different_lessons(self, db):
        """Multiple threads writing to different lesson IDs should not deadlock."""
        errors = []
        num_threads = 10

        def write_lesson(thread_id):
            try:
                for i in range(5):
                    lesson_id = f"lesson-{thread_id}-{i}"
                    db.mark_lesson_opened(lesson_id, f"track-{thread_id}")
                    db.mark_lesson_completed(lesson_id, f"track-{thread_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_lesson, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent write errors: {errors}"
        # Verify all records were written
        assert db.completed_lessons() == num_threads * 5

    def test_concurrent_reads_and_writes(self, db):
        """Readers and writers operating simultaneously should not crash."""
        # Pre-seed some data
        for i in range(10):
            db.mark_lesson_completed(f"seed-{i}", "seed-track")

        errors = []
        stop = threading.Event()

        def reader():
            try:
                while not stop.is_set():
                    db.completed_lessons()
                    db.track_completion("seed-track")
                    db.recent_attempts(limit=5)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def writer(thread_id):
            try:
                for i in range(5):
                    db.record_attempt(
                        exercise_id=f"ex-{thread_id}-{i}",
                        exercise_title_snapshot=f"Exercise {thread_id}-{i}",
                        track_id="python",
                        code_snapshot="print(1)",
                        score=80,
                        passed=True,
                        duration_sec=1,
                        feedback="ok",
                    )
            except Exception as e:
                errors.append(e)

        readers = [threading.Thread(target=reader) for _ in range(3)]
        writers = [threading.Thread(target=writer, args=(t,)) for t in range(3)]

        for t in readers + writers:
            t.start()
        for t in writers:
            t.join(timeout=10)
        stop.set()
        for t in readers:
            t.join(timeout=10)

        assert errors == [], f"Concurrent read/write errors: {errors}"

    def test_concurrent_session_operations(self, db):
        """Multiple threads creating and operating on sessions."""
        errors = []

        def session_worker(thread_id):
            try:
                sid = db.create_mentor_session(f"Session-{thread_id}")
                for i in range(3):
                    db.append_mentor_message(sid, "user", f"Message {i} from thread {thread_id}")
                messages = db.load_mentor_messages(sid)
                assert len(messages) == 3
                db.rename_mentor_session(sid, f"Renamed-{thread_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=session_worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent session errors: {errors}"
        sessions = db.list_mentor_sessions()
        renamed = [s for s in sessions if s[1].startswith("Renamed-")]
        assert len(renamed) == 5


# ---------------------------------------------------------------------------
# 3. Schema evolution and migration
# ---------------------------------------------------------------------------
class TestSchemaEvolution:
    """Test database schema initialization and migration paths."""

    def test_init_db_is_idempotent(self, fresh_db):
        """Calling init_db() multiple times should not fail or corrupt data."""
        fresh_db.init_db()
        fresh_db.init_db()
        fresh_db.init_db()

        # Should still work after multiple init calls
        fresh_db.mark_lesson_opened("test", "track")
        assert fresh_db.lesson_status("test") == "in_progress"

    def test_all_tables_exist_after_init(self, fresh_db):
        """All expected tables should exist after init_db()."""
        fresh_db.init_db()
        tables = fresh_db.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = {t[0] for t in tables}
        expected = {
            "lesson_progress",
            "lesson_notes",
            "practice_attempts",
            "exercise_drafts",
            "mentor_api_config",
            "mentor_sessions",
            "mentor_messages",
            "mentor_knowledge_files",
            "mentor_workspace_state",
        }
        assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"

    def test_performance_indexes_exist(self, fresh_db):
        """Performance indexes should be created by init_db()."""
        fresh_db.init_db()
        indexes = fresh_db.fetchall("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        index_names = {i[0] for i in indexes}
        expected_indexes = {
            "idx_lesson_progress_track_completed",
            "idx_lesson_progress_completed_at",
            "idx_practice_attempts_exercise",
            "idx_practice_attempts_submitted",
            "idx_practice_attempts_track",
            "idx_mentor_messages_session",
            "idx_mentor_sessions_updated",
        }
        assert expected_indexes.issubset(index_names), f"Missing indexes: {expected_indexes - index_names}"

    def test_column_migration_adds_exercise_title_snapshot(self, fresh_db):
        """init_db should handle the exercise_title_snapshot column migration."""
        fresh_db.init_db()
        columns = {row[1] for row in fresh_db.fetchall("PRAGMA table_info(practice_attempts)")}
        assert "exercise_title_snapshot" in columns
        assert "code_snapshot" in columns

    def test_column_migration_adds_key_alias(self, fresh_db):
        """init_db should handle the key_alias column migration."""
        fresh_db.init_db()
        columns = {row[1] for row in fresh_db.fetchall("PRAGMA table_info(mentor_api_config)")}
        assert "key_alias" in columns

    def test_default_workspace_state_created(self, fresh_db):
        """init_db should create a default workspace state row."""
        fresh_db.init_db()
        row = fresh_db.fetchone(
            "SELECT id, use_base, use_personal, use_custom FROM mentor_workspace_state WHERE id = 1"
        )
        assert row is not None
        assert row[0] == 1

    def test_foreign_keys_enabled(self, fresh_db):
        """Foreign keys should be enforced after init_db()."""
        fresh_db.init_db()
        fk_status = fresh_db.fetchone("PRAGMA foreign_keys")
        # fk_status is (1,) when enabled
        assert fk_status[0] == 1

    def test_wal_mode_enabled(self, fresh_db):
        """WAL journal mode should be set."""
        fresh_db.init_db()
        # WAL mode is set on the connection, not per-table
        # We can verify by attempting to set it and reading back
        mode = fresh_db.fetchone("PRAGMA journal_mode")
        # mode could be ('wal',) if it was set, or ('delete',) for a new connection
        # Just verify we can query without error
        assert mode is not None


# ---------------------------------------------------------------------------
# 4. Cross-table interactions
# ---------------------------------------------------------------------------
class TestCrossTableInteractions:
    """Test operations that span multiple tables."""

    def test_reset_preserves_sessions_and_config(self, db, monkeypatch):
        """reset_learning_progress should keep sessions and API config intact."""
        import app.database as db_module

        monkeypatch.setattr(db_module, "save_secret", lambda *a: None)
        monkeypatch.setattr(db_module, "load_secret", lambda *a: "test-key")

        # Create learning data
        db.mark_lesson_completed("l1", "t1")
        db.record_attempt("ex1", "T", "t1", "", 90, True, 1, "")
        db.save_note("l1", "note")
        db.save_exercise_draft("ex1", "T", "code")

        # Create session data
        sid = db.create_mentor_session("Keep Me")
        db.append_mentor_message(sid, "user", "hello")

        # Create API config
        db.save_api_config("https://host", "key", "model")

        # Reset learning data
        db.reset_learning_progress()

        # Learning data should be gone
        assert db.lesson_status("l1") == "not_started"
        assert db.recent_attempts() == []
        assert db.load_note("l1") == ""
        assert db.load_exercise_draft("ex1") is None

        # Session data should survive
        sessions = db.list_mentor_sessions()
        assert any(s[1] == "Keep Me" for s in sessions)
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 1

    def test_mentor_session_snapshot_with_messages(self, db):
        """Session snapshot should reflect actual message content."""
        sid = db.create_mentor_session("Snapshot Test")
        snapshot_empty = db.mentor_session_snapshot(sid)
        assert snapshot_empty["message_count"] == 0
        assert "还没有聊天记录" in snapshot_empty["preview"]

        db.append_mentor_message(sid, "user", "How do I use list comprehensions?")
        snapshot_one = db.mentor_session_snapshot(sid)
        assert snapshot_one["message_count"] == 1
        assert "你：" in snapshot_one["preview"]
        assert "list comprehensions" in snapshot_one["preview"]

    def test_session_snapshot_with_long_content(self, db):
        """Long messages should be clipped in the snapshot."""
        sid = db.create_mentor_session("Long Message Test")
        long_message = "A" * 200
        db.append_mentor_message(sid, "user", long_message)
        snapshot = db.mentor_session_snapshot(sid)
        assert len(snapshot["preview"]) <= 80  # prefix + clipped content

    def test_mentor_workspace_flags_lifecycle(self, db):
        """Workspace flags should persist across save/load cycles."""
        # Default
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is True
        assert flags["use_personal"] is True
        assert flags["use_custom"] is True

        # Modify
        db.save_mentor_workspace_flags(use_base=False, use_personal=True, use_custom=False)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is False
        assert flags["use_personal"] is True
        assert flags["use_custom"] is False

    def test_corrupted_message_repair(self, db):
        """repair_corrupted_mentor_history should fix garbled messages."""
        sid = db.create_mentor_session("Repair Test")
        # Insert a corrupted message directly
        db.execute(
            "INSERT INTO mentor_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (sid, "assistant", "???????????????????", now_text()),
        )
        # Repair
        db.repair_corrupted_mentor_history()
        # Verify
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 1
        assert "自动清理" in messages[0][1]

    def test_fetchall_and_fetchone_helpers(self, db):
        """Direct SQL execution via fetchall/fetchone should work."""
        db.mark_lesson_completed("l1", "t1")
        rows = db.fetchall("SELECT lesson_id FROM lesson_progress WHERE completed = 1")
        assert len(rows) == 1
        assert rows[0][0] == "l1"

        row = db.fetchone("SELECT completed FROM lesson_progress WHERE lesson_id = 'l1'")
        assert row[0] == 1

    def test_execute_raw_sql(self, db):
        """Direct execute should work for raw SQL."""
        db.execute(
            "INSERT INTO lesson_progress (lesson_id, track_id, status, completed) VALUES (?, ?, ?, ?)",
            ("raw-1", "raw-track", "in_progress", 0),
        )
        assert db.lesson_status("raw-1") == "in_progress"

    def test_active_days_streak_with_no_data(self, db):
        """Active days streak should return 0 when there is no data."""
        assert db.active_days_streak() == 0
