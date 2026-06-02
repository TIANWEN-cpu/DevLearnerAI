"""Tests for app.utils.events -- Event bus and typed events."""

import threading
from unittest.mock import MagicMock

import pytest

from app.utils.events import (
    AchievementUnlockedEvent,
    AppErrorEvent,
    BookmarkAddedEvent,
    BookmarkRemovedEvent,
    DataExportedEvent,
    DataImportedEvent,
    DataResetEvent,
    EventBus,
    ExerciseAttemptRecordedEvent,
    ExerciseDraftClearedEvent,
    ExerciseDraftSavedEvent,
    FontSizeChangedEvent,
    KnowledgeFileAddedEvent,
    KnowledgeFileRemovedEvent,
    LessonCompletedEvent,
    LessonNoteSavedEvent,
    LessonOpenedEvent,
    MentorMessageSentEvent,
    MentorSessionCreatedEvent,
    MentorSessionDeletedEvent,
    MentorSessionSwitchedEvent,
    NavigationEvent,
    ReviewCompletedEvent,
    ThemeChangedEvent,
    event_bus,
)


class TestEventBase:
    """Test the Event base class."""

    def test_event_has_timestamp(self):
        event = LessonOpenedEvent(lesson_id="test")
        assert event.timestamp is not None

    def test_event_is_frozen(self):
        event = LessonOpenedEvent(lesson_id="test")
        with pytest.raises(AttributeError):
            event.lesson_id = "changed"

    def test_event_name(self):
        assert LessonOpenedEvent.event_name() == "LessonOpenedEvent"
        assert AchievementUnlockedEvent.event_name() == "AchievementUnlockedEvent"


class TestEventBus:
    """Test EventBus publish/subscribe."""

    def setup_method(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        handler = MagicMock()
        self.bus.subscribe(LessonOpenedEvent, handler)
        event = LessonOpenedEvent(lesson_id="py-01", track_id="python")
        self.bus.publish(event)
        handler.assert_called_once_with(event)

    def test_unsubscribe(self):
        handler = MagicMock()
        self.bus.subscribe(LessonOpenedEvent, handler)
        self.bus.unsubscribe(LessonOpenedEvent, handler)
        self.bus.publish(LessonOpenedEvent())
        handler.assert_not_called()

    def test_unsubscribe_nonexistent(self):
        handler = MagicMock()
        self.bus.unsubscribe(LessonOpenedEvent, handler)  # should not raise

    def test_multiple_handlers(self):
        h1 = MagicMock()
        h2 = MagicMock()
        self.bus.subscribe(LessonCompletedEvent, h1)
        self.bus.subscribe(LessonCompletedEvent, h2)
        event = LessonCompletedEvent()
        self.bus.publish(event)
        h1.assert_called_once_with(event)
        h2.assert_called_once_with(event)

    def test_handler_not_called_for_different_event_type(self):
        handler = MagicMock()
        self.bus.subscribe(LessonOpenedEvent, handler)
        self.bus.publish(LessonCompletedEvent())
        handler.assert_not_called()

    def test_handler_exception_does_not_propagate(self):
        def bad_handler(event):
            raise RuntimeError("boom")

        good_handler = MagicMock()
        self.bus.subscribe(LessonOpenedEvent, bad_handler)
        self.bus.subscribe(LessonOpenedEvent, good_handler)
        self.bus.publish(LessonOpenedEvent())
        good_handler.assert_called_once()

    def test_no_duplicate_subscriptions(self):
        handler = MagicMock()
        self.bus.subscribe(LessonOpenedEvent, handler)
        self.bus.subscribe(LessonOpenedEvent, handler)
        self.bus.publish(LessonOpenedEvent())
        handler.assert_called_once()

    def test_subscriber_count(self):
        assert self.bus.subscriber_count(LessonOpenedEvent) == 0
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        assert self.bus.subscriber_count(LessonOpenedEvent) == 1

    def test_clear_specific_type(self):
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        self.bus.subscribe(LessonCompletedEvent, MagicMock())
        self.bus.clear(LessonOpenedEvent)
        assert self.bus.subscriber_count(LessonOpenedEvent) == 0
        assert self.bus.subscriber_count(LessonCompletedEvent) == 1

    def test_clear_all(self):
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        self.bus.subscribe(LessonCompletedEvent, MagicMock())
        self.bus.clear()
        assert self.bus.subscriber_count(LessonOpenedEvent) == 0
        assert self.bus.subscriber_count(LessonCompletedEvent) == 0

    def test_handler_count(self):
        assert self.bus.handler_count() == 0
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        self.bus.subscribe(LessonCompletedEvent, MagicMock())
        assert self.bus.handler_count() == 3

    def test_registered_event_types(self):
        self.bus.subscribe(LessonOpenedEvent, MagicMock())
        types = self.bus.registered_event_types()
        assert LessonOpenedEvent in types

    def test_thread_safety(self):
        results = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                results.append(event.lesson_id)

        self.bus.subscribe(LessonOpenedEvent, handler)

        threads = []
        for i in range(10):
            t = threading.Thread(
                target=self.bus.publish,
                args=(LessonOpenedEvent(lesson_id=f"lesson-{i}"),),
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 10


class TestGlobalEventBus:
    """Test the global event_bus singleton."""

    def test_global_bus_exists(self):
        assert event_bus is not None
        assert isinstance(event_bus, EventBus)


class TestDomainEvents:
    """Test all domain event types have correct fields."""

    def test_lesson_opened(self):
        e = LessonOpenedEvent(lesson_id="l1", track_id="t1")
        assert e.lesson_id == "l1"
        assert e.track_id == "t1"

    def test_lesson_completed(self):
        e = LessonCompletedEvent(lesson_id="l1", track_id="t1")
        assert e.lesson_id == "l1"
        assert e.track_id == "t1"

    def test_lesson_note_saved(self):
        e = LessonNoteSavedEvent(lesson_id="l1", has_content=True)
        assert e.has_content is True

    def test_exercise_attempt(self):
        e = ExerciseAttemptRecordedEvent(exercise_id="ex1", score=95, passed=True, duration_sec=30)
        assert e.score == 95
        assert e.passed is True

    def test_exercise_draft_saved(self):
        e = ExerciseDraftSavedEvent(exercise_id="ex1")
        assert e.exercise_id == "ex1"

    def test_exercise_draft_cleared(self):
        e = ExerciseDraftClearedEvent(exercise_id="ex1")
        assert e.exercise_id == "ex1"

    def test_review_completed(self):
        e = ReviewCompletedEvent(exercise_id="ex1", quality=4)
        assert e.quality == 4

    def test_mentor_session_created(self):
        e = MentorSessionCreatedEvent(session_id=1, session_name="test")
        assert e.session_id == 1

    def test_mentor_session_deleted(self):
        e = MentorSessionDeletedEvent(session_id=5)
        assert e.session_id == 5

    def test_mentor_session_switched(self):
        e = MentorSessionSwitchedEvent(session_id=3)
        assert e.session_id == 3

    def test_mentor_message_sent(self):
        e = MentorMessageSentEvent(session_id=1, role="user")
        assert e.role == "user"

    def test_bookmark_added(self):
        e = BookmarkAddedEvent(item_type="lesson", item_id="l1", title="Lesson 1")
        assert e.title == "Lesson 1"

    def test_bookmark_removed(self):
        e = BookmarkRemovedEvent(item_type="lesson", item_id="l1")
        assert e.item_type == "lesson"

    def test_achievement_unlocked(self):
        e = AchievementUnlockedEvent(
            achievement_id="first_lesson", title="Beginner", description="Complete first lesson"
        )
        assert e.title == "Beginner"

    def test_knowledge_file_added(self):
        e = KnowledgeFileAddedEvent(display_name="Readme", file_path="/path")
        assert e.display_name == "Readme"

    def test_knowledge_file_removed(self):
        e = KnowledgeFileRemovedEvent(file_id=42)
        assert e.file_id == 42

    def test_data_reset(self):
        e = DataResetEvent()
        assert e.timestamp is not None

    def test_data_imported(self):
        e = DataImportedEvent(record_count=100)
        assert e.record_count == 100

    def test_data_exported(self):
        e = DataExportedEvent(format="json")
        assert e.format == "json"

    def test_theme_changed(self):
        e = ThemeChangedEvent(dark_mode=True)
        assert e.dark_mode is True

    def test_font_size_changed(self):
        e = FontSizeChangedEvent(font_size="large")
        assert e.font_size == "large"

    def test_navigation(self):
        e = NavigationEvent(page_name="dashboard")
        assert e.page_name == "dashboard"

    def test_app_error(self):
        e = AppErrorEvent(category="database", message="fail", context="saving")
        assert e.category == "database"
