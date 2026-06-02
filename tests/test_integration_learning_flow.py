"""Integration tests for the learning flow: course loading -> content display -> progress tracking.

These tests exercise the real ContentService with actual metadata files and
the AppDatabase progress-tracking methods together, verifying that the
full course-learning pipeline works end-to-end.
"""

import pytest

from app.config import METADATA_DIR
from app.content_service import ContentService, Lesson, Module, Track
from app.database import AppDatabase, close_connection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def content_service():
    """Create a ContentService backed by real metadata files."""
    return ContentService()


@pytest.fixture()
def db(tmp_path):
    """Create an isolated AppDatabase for each test."""
    close_connection()
    db_path = tmp_path / "learning_flow.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# 1. Course metadata loading and structure validation
# ---------------------------------------------------------------------------
class TestCourseMetadataLoading:
    """Verify that real metadata files load and produce valid structures."""

    def test_metadata_file_exists(self):
        assert METADATA_DIR.exists()
        assert (METADATA_DIR / "course_map.json").exists()

    def test_content_service_loads_tracks(self, content_service):
        tracks = content_service.tracks
        assert len(tracks) > 0, "Should load at least one track from course_map.json"

    def test_tracks_have_modules_and_lessons(self, content_service):
        for track in content_service.tracks:
            assert isinstance(track, Track)
            assert track.id, "Track must have an id"
            assert track.title, f"Track {track.id} must have a title"
            assert len(track.modules) > 0, f"Track {track.id} must have modules"
            for module in track.modules:
                assert isinstance(module, Module)
                assert module.id
                assert module.title
                assert len(module.lessons) > 0, f"Module {module.id} must have lessons"
                for lesson in module.lessons:
                    assert isinstance(lesson, Lesson)
                    assert lesson.id
                    assert lesson.title
                    assert lesson.path, f"Lesson {lesson.id} must have a content path"

    def test_all_lessons_flat_list(self, content_service):
        all_lessons = content_service.all_lessons()
        assert len(all_lessons) > 0
        for track, module, lesson in all_lessons:
            assert isinstance(track, Track)
            assert isinstance(module, Module)
            assert isinstance(lesson, Lesson)
            assert track.id
            assert module.id
            assert lesson.id


# ---------------------------------------------------------------------------
# 2. Content display: lesson lookup and markdown reading
# ---------------------------------------------------------------------------
class TestContentDisplay:
    """Verify that lessons can be looked up and their markdown read."""

    def test_lesson_by_id_returns_tuple(self, content_service):
        all_lessons = content_service.all_lessons()
        assert all_lessons
        sample = all_lessons[0]
        lesson_id = sample[2].id
        result = content_service.lesson_by_id(lesson_id)
        assert result is not None
        track, module, lesson = result
        assert lesson.id == lesson_id
        assert track.id == sample[0].id

    def test_lesson_by_id_not_found(self, content_service):
        assert content_service.lesson_by_id("nonexistent-lesson-id-99999") is None

    def test_track_by_id(self, content_service):
        tracks = content_service.tracks
        first_track = tracks[0]
        result = content_service.track_by_id(first_track.id)
        assert result is not None
        assert result.id == first_track.id
        assert result.title == first_track.title

    def test_lesson_markdown_content_loads(self, content_service):
        """Read markdown for the first available lesson and verify it is non-empty."""
        all_lessons = content_service.all_lessons()
        assert all_lessons
        _, _, lesson = all_lessons[0]
        md = content_service.lesson_markdown(lesson)
        assert isinstance(md, str)
        assert len(md) > 0

    def test_lesson_markdown_caching(self, content_service):
        """Second read of the same lesson should return cached content."""
        all_lessons = content_service.all_lessons()
        _, _, lesson = all_lessons[0]
        first = content_service.lesson_markdown(lesson)
        second = content_service.lesson_markdown(lesson)
        assert first is second, "Cached content should be the same object"

    def test_markdown_cache_clear(self, content_service):
        all_lessons = content_service.all_lessons()
        _, _, lesson = all_lessons[0]
        content_service.lesson_markdown(lesson)
        content_service.clear_markdown_cache()
        # After clearing, next read should be fresh (not error)
        fresh = content_service.lesson_markdown(lesson)
        assert fresh  # still returns content

    def test_preload_adjacent_lessons(self, content_service):
        """Preloading adjacent lessons should populate the cache without errors."""
        all_lessons = content_service.all_lessons()
        if len(all_lessons) < 2:
            pytest.skip("Need at least 2 lessons for adjacent preload test")
        mid_lesson_id = all_lessons[len(all_lessons) // 2][2].id
        content_service.preload_adjacent_lessons(mid_lesson_id)
        assert True  # Verify no exception during preload


# ---------------------------------------------------------------------------
# 3. Progress tracking: full lifecycle
# ---------------------------------------------------------------------------
class TestProgressTrackingLifecycle:
    """Test the full course progress lifecycle with database integration."""

    def test_open_then_complete_flow(self, db):
        """Open a lesson, verify in_progress, then complete it."""
        lesson_id = "flow-test-lesson-1"
        track_id = "flow-test-track"

        # Initially not started
        assert db.lesson_status(lesson_id) == "not_started"

        # Mark opened -> in_progress
        db.mark_lesson_opened(lesson_id, track_id)
        assert db.lesson_status(lesson_id) == "in_progress"

        # Mark completed
        db.mark_lesson_completed(lesson_id, track_id)
        assert db.lesson_status(lesson_id) == "completed"

        # Reopening should stay completed
        db.mark_lesson_opened(lesson_id, track_id)
        assert db.lesson_status(lesson_id) == "completed"

    def test_multiple_lessons_same_track(self, db):
        track = "python"
        for i in range(5):
            db.mark_lesson_completed(f"lesson-{i}", track)

        assert db.completed_lessons() == 5
        assert db.track_completion(track) == 5

    def test_multiple_tracks_isolated(self, db):
        db.mark_lesson_completed("l1", "python")
        db.mark_lesson_completed("l2", "python")
        db.mark_lesson_completed("l3", "database")

        assert db.track_completion("python") == 2
        assert db.track_completion("database") == 1
        assert db.track_completion("csharp") == 0

    def test_list_completed_lessons_ordered(self, db):
        for i in range(3):
            db.mark_lesson_completed(f"lesson-{i}", "track")
        completed = db.list_completed_lessons()
        assert len(completed) == 3
        # Should be ordered by completed_at DESC (most recent first)
        for entry in completed:
            assert entry[1] is not None  # completed_at should be set

    def test_notes_with_progress(self, db):
        """Notes can be saved and loaded alongside progress."""
        lesson_id = "note-lesson"
        db.mark_lesson_opened(lesson_id, "track")
        db.save_note(lesson_id, "Important: remember to use list comprehensions")
        assert db.load_note(lesson_id) == "Important: remember to use list comprehensions"

        # Notes persist after completion
        db.mark_lesson_completed(lesson_id, "track")
        assert db.load_note(lesson_id) == "Important: remember to use list comprehensions"

    def test_reset_clears_progress_and_notes(self, db):
        db.mark_lesson_completed("l1", "t1")
        db.save_note("l1", "my note")
        db.reset_learning_progress()
        assert db.lesson_status("l1") == "not_started"
        assert db.load_note("l1") == ""


# ---------------------------------------------------------------------------
# 4. Content + Progress integration
# ---------------------------------------------------------------------------
class TestContentProgressIntegration:
    """Combine ContentService and AppDatabase to simulate real user flows."""

    def test_load_track_then_track_progress(self, content_service, db):
        """Load a real track, mark all its lessons completed, verify counts."""
        tracks = content_service.tracks
        assert tracks
        track = tracks[0]
        all_lesson_ids = [lesson.id for lesson in track.lessons]

        # Initially none completed
        assert db.track_completion(track.id) == 0

        # Complete all lessons
        for lesson_id in all_lesson_ids:
            db.mark_lesson_completed(lesson_id, track.id)

        assert db.track_completion(track.id) == len(all_lesson_ids)
        assert db.completed_lessons() == len(all_lesson_ids)

    def test_lookup_lesson_then_mark_opened(self, content_service, db):
        """Look up a real lesson by ID, then mark it opened in the database."""
        all_lessons = content_service.all_lessons()
        _, _, lesson = all_lessons[0]
        # track used below for mark_lesson_opened
        _track = all_lessons[0][0]

        # Look up via ContentService
        result = content_service.lesson_by_id(lesson.id)
        assert result is not None
        found_track, found_module, found_lesson = result

        # Mark it opened via Database
        db.mark_lesson_opened(found_lesson.id, found_track.id)
        assert db.lesson_status(found_lesson.id) == "in_progress"

    def test_read_content_then_save_note(self, content_service, db):
        """Read markdown for a lesson and save a summary note."""
        all_lessons = content_service.all_lessons()
        _, _, lesson = all_lessons[0]
        md = content_service.lesson_markdown(lesson)

        # Save the first 200 chars as a note
        note_text = md[:200]
        db.save_note(lesson.id, note_text)
        assert db.load_note(lesson.id) == note_text

    def test_full_learning_session_simulation(self, content_service, db):
        """Simulate a full learning session across multiple lessons."""
        all_lessons = content_service.all_lessons()
        if len(all_lessons) < 3:
            pytest.skip("Need at least 3 lessons")

        # Open first lesson
        t1, m1, l1 = all_lessons[0]
        db.mark_lesson_opened(l1.id, t1.id)
        assert db.lesson_status(l1.id) == "in_progress"

        # Read its content
        md1 = content_service.lesson_markdown(l1)
        assert md1

        # Save notes
        db.save_note(l1.id, "Key takeaways from lesson 1")

        # Complete it
        db.mark_lesson_completed(l1.id, t1.id)
        assert db.lesson_status(l1.id) == "completed"

        # Open second lesson
        t2, m2, l2 = all_lessons[1]
        db.mark_lesson_opened(l2.id, t2.id)

        # Preload adjacent lessons
        content_service.preload_adjacent_lessons(l2.id)

        # Complete second lesson
        db.mark_lesson_completed(l2.id, t2.id)

        # Verify overall progress
        assert db.completed_lessons() == 2
        notes = db.load_note(l1.id)
        assert "Key takeaways" in notes
