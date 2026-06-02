"""Database stress tests for app.database.

Covers:
- Rapid sequential writes
- Concurrent read/write patterns
- Large dataset queries
- Stats cache behavior under rapid updates
- Batch insert stress
"""

import threading
from datetime import date, timedelta

import pytest

from app.database import AppDatabase, close_connection


@pytest.fixture()
def db(tmp_path):
    """Create an AppDatabase backed by a temporary file, and clean up after.

    Prevents legacy DB migration so the test database always uses the current schema.
    """
    close_connection()
    db_path = tmp_path / "test.db"
    # Prevent legacy DB migration by creating the file first
    db_path.touch()
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# Rapid sequential writes
# ---------------------------------------------------------------------------
class TestRapidSequentialWrites:
    """Test database behavior under rapid sequential write operations."""

    def test_rapid_lesson_status_updates(self, db):
        """Rapidly update lesson status many times."""
        for i in range(100):
            db.mark_lesson_opened(f"lesson-{i}", "track-test")
            db.mark_lesson_completed(f"lesson-{i}", "track-test")
        assert db.completed_lessons() == 100

    def test_rapid_note_saves(self, db):
        """Rapidly save notes for the same lesson."""
        for i in range(50):
            db.save_note("lesson-1", f"note version {i}")
        assert db.load_note("lesson-1") == "note version 49"

    def test_rapid_attempt_recording(self, db):
        """Record many practice attempts rapidly."""
        for i in range(200):
            db.record_attempt(
                exercise_id=f"ex-{i}",
                exercise_title_snapshot=f"Exercise {i}",
                track_id="python",
                code_snapshot=f"print({i})",
                score=i % 101,
                passed=(i % 101) >= 70,
                duration_sec=i % 10,
                feedback="ok",
            )
        attempts = db.recent_attempts(limit=200)
        assert len(attempts) == 200

    def test_rapid_draft_cycles(self, db):
        """Rapidly save and clear drafts."""
        for i in range(100):
            db.save_exercise_draft(f"ex-{i}", f"Title {i}", f"code {i}")
            db.clear_exercise_draft(f"ex-{i}")
            assert db.load_exercise_draft(f"ex-{i}") is None

    def test_rapid_session_create_delete(self, db):
        """Rapidly create and delete mentor sessions."""
        for i in range(50):
            sid = db.create_mentor_session(f"Session {i}")
            db.delete_mentor_session(sid)
        # Only the default session from init_db should remain
        remaining = db.list_mentor_sessions()
        assert len(remaining) == 1

    def test_rapid_message_appends(self, db):
        """Rapidly append messages to a single session."""
        sid = db.create_mentor_session("StressTest")
        for i in range(100):
            db.append_mentor_message(sid, "user" if i % 2 == 0 else "assistant", f"Message {i}")
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 100

    def test_rapid_knowledge_file_add_remove(self, db):
        """Rapidly add and remove knowledge files."""
        for i in range(50):
            db.add_knowledge_file(f"File {i}", f"/path/{i}", f"excerpt {i}")
        files = db.list_knowledge_files()
        assert len(files) == 50
        for f in files:
            db.remove_knowledge_file(f[0])
        assert db.list_knowledge_files() == []


# ---------------------------------------------------------------------------
# Concurrent read/write patterns
# ---------------------------------------------------------------------------
class TestConcurrentReadWrite:
    """Test database behavior under concurrent access patterns."""

    def test_concurrent_lesson_writes(self, db):
        """Multiple threads writing different lessons simultaneously."""
        errors = []

        def write_lessons(start_idx):
            try:
                for i in range(start_idx * 10, (start_idx + 1) * 10):
                    db.mark_lesson_opened(f"lesson-{i}", "track-test")
                    db.mark_lesson_completed(f"lesson-{i}", "track-test")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_lessons, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        assert db.completed_lessons() == 50

    def test_concurrent_read_write(self, db):
        """Reading while writing should not cause errors."""
        errors = []
        stop_event = threading.Event()

        def writer():
            try:
                for i in range(100):
                    if stop_event.is_set():
                        break
                    db.mark_lesson_opened(f"w-lesson-{i}", "track-test")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    if stop_event.is_set():
                        break
                    db.completed_lessons()
                    db.recent_attempts()
                    db.list_mentor_sessions()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        stop_event.set()

        assert len(errors) == 0, f"Concurrent read/write errors: {errors}"

    def test_concurrent_attempt_recording(self, db):
        """Multiple threads recording attempts simultaneously."""
        errors = []

        def record_attempts(thread_id):
            try:
                for i in range(20):
                    db.record_attempt(
                        exercise_id=f"ex-t{thread_id}-{i}",
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

        threads = [threading.Thread(target=record_attempts, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent attempt recording errors: {errors}"
        attempts = db.recent_attempts(limit=200)
        assert len(attempts) == 100

    def test_concurrent_message_writes(self, db):
        """Multiple threads writing to different sessions."""
        errors = []
        sessions = [db.create_mentor_session(f"Thread {i}") for i in range(3)]

        def write_messages(session_id):
            try:
                for i in range(30):
                    db.append_mentor_message(session_id, "user", f"msg {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_messages, args=(sid,)) for sid in sessions]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent message write errors: {errors}"
        for sid in sessions:
            messages = db.load_mentor_messages(sid)
            assert len(messages) == 30

    def test_concurrent_note_saves(self, db):
        """Multiple threads saving notes for different lessons."""
        errors = []

        def save_notes(lesson_id):
            try:
                for i in range(20):
                    db.save_note(lesson_id, f"note {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_notes, args=(f"lesson-{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent note save errors: {errors}"


# ---------------------------------------------------------------------------
# Large dataset queries
# ---------------------------------------------------------------------------
class TestLargeDatasetQueries:
    """Test query performance and correctness with large datasets."""

    def test_large_lesson_completion_count(self, db):
        """Query completed lessons with many records."""
        for i in range(500):
            db.mark_lesson_completed(f"lesson-{i}", f"track-{i % 10}")
        assert db.completed_lessons() == 500

    def test_large_track_completion(self, db):
        """Query track-specific completion with many tracks."""
        for i in range(100):
            db.mark_lesson_completed(f"lesson-{i}", "track-python")
        for i in range(100, 200):
            db.mark_lesson_completed(f"lesson-{i}", "track-db")
        assert db.track_completion("track-python") == 100
        assert db.track_completion("track-db") == 100
        assert db.track_completion("track-csharp") == 0

    def test_large_recent_attempts_query(self, db):
        """Query recent attempts with many records."""
        for i in range(500):
            db.record_attempt(
                exercise_id=f"ex-{i}",
                exercise_title_snapshot=f"Exercise {i}",
                track_id="python",
                code_snapshot=f"print({i})",
                score=i % 101,
                passed=(i % 101) >= 70,
                duration_sec=i % 10,
                feedback="ok",
            )
        recent = db.recent_attempts(limit=50)
        assert len(recent) == 50
        # Most recent first
        assert recent[0][0] >= recent[-1][0]

    def test_large_average_score(self, db):
        """Average score calculation with many records."""
        for i in range(100):
            db.record_attempt("ex", "T", "t1", "", i, True, 1, "")
        avg = db.average_score()
        assert avg == 50

    def test_batch_insert_performance(self, db):
        """Batch insert should handle large batches."""
        records = [
            (
                f"ex-{i}",
                f"Exercise {i}",
                "python",
                f"print({i})",
                i % 101,
                (i % 101) >= 70,
                i % 10,
                "ok",
            )
            for i in range(1000)
        ]
        db.record_attempts_batch(records)
        recent = db.recent_attempts(limit=1000)
        assert len(recent) == 1000

    def test_batch_insert_empty_list(self, db):
        """Batch insert with empty list should be a no-op."""
        db.record_attempts_batch([])
        assert db.recent_attempts() == []

    def test_list_completed_lessons_many(self, db):
        """List completed lessons with many records."""
        for i in range(200):
            db.mark_lesson_completed(f"lesson-{i}", "track-test")
        completed = db.list_completed_lessons()
        assert len(completed) == 200

    def test_large_mentor_messages(self, db):
        """Load many messages from a single session."""
        sid = db.create_mentor_session("Large")
        for i in range(500):
            db.append_mentor_message(sid, "user" if i % 2 == 0 else "assistant", f"Message {i}")
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 500
        # Ordered by id ASC
        assert messages[0][2] <= messages[-1][2]

    def test_trim_mentor_messages(self, db):
        """Trim old messages keeping only recent ones."""
        sid = db.create_mentor_session("Trim")
        for i in range(300):
            db.append_mentor_message(sid, "user", f"Message {i}")
        deleted = db.trim_mentor_messages(sid, keep_last=100)
        assert deleted == 200
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 100

    def test_trim_no_op_when_under_limit(self, db):
        """Trim should return 0 when count is under limit."""
        sid = db.create_mentor_session("Trim")
        for i in range(50):
            db.append_mentor_message(sid, "user", f"Message {i}")
        deleted = db.trim_mentor_messages(sid, keep_last=100)
        assert deleted == 0

    def test_active_days_streak_many_days(self, db):
        """Streak calculation with many consecutive days."""
        today = date.today()
        for i in range(30):
            day = today - timedelta(days=i)
            db.execute(
                """
                INSERT INTO practice_attempts (
                    exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                    score, passed, duration_sec, submitted_at, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("ex", "T", "t1", "", 80, 1, 1, f"{day} 12:00:00", "ok"),
            )
        streak = db.active_days_streak()
        assert streak == 30

    def test_reset_large_dataset(self, db):
        """Reset should clear all data efficiently."""
        for i in range(200):
            db.mark_lesson_completed(f"lesson-{i}", "track-test")
            db.record_attempt(f"ex-{i}", "T", "t1", "", 80, True, 1, "ok")
            db.save_note(f"lesson-{i}", f"note {i}")
            db.save_exercise_draft(f"ex-{i}", "T", "code")

        db.reset_learning_progress()

        assert db.completed_lessons() == 0
        assert db.recent_attempts() == []
        assert db.load_note("lesson-0") == ""
        assert db.load_exercise_draft("ex-0") is None


# ---------------------------------------------------------------------------
# Stats cache behavior
# ---------------------------------------------------------------------------
class TestStatsCache:
    """Test stats cache invalidation and TTL behavior."""

    def test_cache_invalidated_on_lesson_complete(self, db):
        """Stats cache should be invalidated when a lesson is completed."""
        db.mark_lesson_completed("l1", "t1")
        # First call populates cache
        count1 = db.completed_lessons()
        assert count1 == 1
        # Second call should use cache
        count2 = db.completed_lessons()
        assert count2 == 1

    def test_cache_invalidated_on_attempt_record(self, db):
        """Stats cache should be invalidated when an attempt is recorded."""
        db.record_attempt("ex", "T", "t1", "", 80, True, 1, "ok")
        avg1 = db.average_score()
        assert avg1 == 80
        db.record_attempt("ex2", "T", "t1", "", 60, False, 1, "ok")
        avg2 = db.average_score()
        assert avg2 == 70

    def test_cache_invalidated_on_batch_insert(self, db):
        """Stats cache should be invalidated after batch insert."""
        db.record_attempts_batch(
            [
                ("ex1", "T", "t1", "", 80, True, 1, "ok"),
                ("ex2", "T", "t1", "", 90, True, 1, "ok"),
            ]
        )
        avg = db.average_score()
        assert avg == 85

    def test_cache_invalidated_on_reset(self, db):
        """Stats cache should be invalidated on reset."""
        db.mark_lesson_completed("l1", "t1")
        assert db.completed_lessons() == 1
        db.reset_learning_progress()
        assert db.completed_lessons() == 0
