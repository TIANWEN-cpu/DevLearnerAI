"""Tests for app.services -- Service layer wrapping database calls."""

from unittest.mock import MagicMock, patch

import app.services as services_pkg
from app.services.achievement_service import AchievementService
from app.services.bookmark_service import BookmarkService
from app.services.config_service import ConfigService
from app.services.lesson_service import LessonService
from app.services.mentor_service import MentorService


class TestServiceImports:
    """Test that the services package exports all service classes."""

    def test_all_exports(self):
        assert hasattr(services_pkg, "BaseService")
        assert hasattr(services_pkg, "AchievementService")
        assert hasattr(services_pkg, "BookmarkService")
        assert hasattr(services_pkg, "ConfigService")
        assert hasattr(services_pkg, "LessonService")
        assert hasattr(services_pkg, "MentorService")
        assert hasattr(services_pkg, "NoteService")
        assert hasattr(services_pkg, "PracticeDataService")
        assert hasattr(services_pkg, "ReviewService")


class TestLessonService:
    """Test LessonService delegates to database and publishes events."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = LessonService(self.db)

    def test_mark_opened_delegates(self):
        self.service.mark_opened("l1", "t1")
        self.db.mark_lesson_opened.assert_called_once_with("l1", "t1")

    def test_mark_opened_publishes_event(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.mark_opened("l1", "t1")
            mock_bus.publish.assert_called_once()
            event = mock_bus.publish.call_args[0][0]
            assert event.lesson_id == "l1"
            assert event.track_id == "t1"

    def test_mark_completed_delegates(self):
        self.service.mark_completed("l1", "t1")
        self.db.mark_lesson_completed.assert_called_once_with("l1", "t1")

    def test_mark_completed_publishes_event(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.mark_completed("l1", "t1")
            mock_bus.publish.assert_called_once()
            event = mock_bus.publish.call_args[0][0]
            assert event.lesson_id == "l1"

    def test_get_status(self):
        self.db.lesson_status.return_value = "completed"
        assert self.service.get_status("l1") == "completed"
        self.db.lesson_status.assert_called_once_with("l1")

    def test_get_track_completion(self):
        self.db.track_completion.return_value = 5
        assert self.service.get_track_completion("t1") == 5

    def test_get_completed_count(self):
        self.db.completed_lessons.return_value = 10
        assert self.service.get_completed_count() == 10

    def test_list_completed(self):
        self.db.list_completed_lessons.return_value = [("l1", "2024-01-01")]
        result = self.service.list_completed()
        assert result == [("l1", "2024-01-01")]

    def test_get_streak(self):
        self.db.active_days_streak.return_value = 7
        assert self.service.get_streak() == 7


class TestBookmarkService:
    """Test BookmarkService."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = BookmarkService(self.db)

    def test_add_delegates_and_publishes(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.add("lesson", "l1", "Lesson 1")
            self.db.add_bookmark.assert_called_once_with("lesson", "l1", "Lesson 1", "", "")
            mock_bus.publish.assert_called_once()

    def test_remove_delegates_and_publishes(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.remove("lesson", "l1")
            self.db.remove_bookmark.assert_called_once_with("lesson", "l1")
            mock_bus.publish.assert_called_once()

    def test_is_bookmarked(self):
        self.db.is_bookmarked.return_value = True
        assert self.service.is_bookmarked("lesson", "l1") is True

    def test_list_all(self):
        self.db.list_bookmarks.return_value = []
        assert self.service.list_all() == []

    def test_search(self):
        self.db.search_bookmarks.return_value = []
        assert self.service.search("query") == []

    def test_count(self):
        self.db.bookmark_count.return_value = 42
        assert self.service.count() == 42


class TestMentorService:
    """Test MentorService."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = MentorService(self.db)

    def test_create_session(self):
        self.db.create_mentor_session.return_value = 1
        with patch("app.services.base.event_bus") as mock_bus:
            result = self.service.create_session("test")
            assert result == 1
            mock_bus.publish.assert_called_once()

    def test_delete_session(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.delete_session(5)
            self.db.delete_mentor_session.assert_called_once_with(5)
            mock_bus.publish.assert_called_once()

    def test_rename_session(self):
        self.service.rename_session(1, "new name")
        self.db.rename_mentor_session.assert_called_once_with(1, "new name")

    def test_list_sessions(self):
        self.db.list_mentor_sessions.return_value = [(1, "test", "2024-01-01")]
        assert self.service.list_sessions() == [(1, "test", "2024-01-01")]

    def test_set_active_publishes_event(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.set_active(3)
            self.db.set_active_mentor_session.assert_called_once_with(3)
            mock_bus.publish.assert_called_once()

    def test_get_active_id(self):
        self.db.load_active_mentor_session_id.return_value = 5
        assert self.service.get_active_id() == 5

    def test_append_message_publishes_event(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.append_message(1, "user", "hello")
            self.db.append_mentor_message.assert_called_once_with(1, "user", "hello")
            mock_bus.publish.assert_called_once()

    def test_load_messages(self):
        self.db.load_mentor_messages.return_value = [("user", "hi", "2024-01-01")]
        assert self.service.load_messages(1) == [("user", "hi", "2024-01-01")]

    def test_trim_messages(self):
        self.db.trim_mentor_messages.return_value = 50
        assert self.service.trim_messages(1, 200) == 50

    def test_save_workspace_flags(self):
        self.service.save_workspace_flags(True, False, True)
        self.db.save_mentor_workspace_flags.assert_called_once_with(True, False, True)

    def test_load_workspace_flags(self):
        self.db.load_mentor_workspace_flags.return_value = {"use_base": True}
        assert self.service.load_workspace_flags() == {"use_base": True}


class TestConfigService:
    """Test ConfigService."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = ConfigService(self.db)

    def test_save_api_config(self):
        self.service.save_api_config("host", "key", "model")
        self.db.save_api_config.assert_called_once_with("host", "key", "model")

    def test_load_api_config(self):
        self.db.load_api_config.return_value = ("h", "k", "m")
        assert self.service.load_api_config() == ("h", "k", "m")

    def test_reset_all_publishes_event(self):
        with patch("app.services.base.event_bus") as mock_bus:
            self.service.reset_all()
            self.db.reset_learning_progress.assert_called_once()
            mock_bus.publish.assert_called_once()

    def test_export_json(self):
        self.db.export_progress_json.return_value = {"version": "2.0"}
        with patch("app.services.base.event_bus"):
            result = self.service.export_json()
            assert result == {"version": "2.0"}

    def test_import_json(self):
        self.db.import_progress_json.return_value = 100
        with patch("app.services.base.event_bus"):
            result = self.service.import_json({"data": "here"})
            assert result == 100


class TestAchievementService:
    """Test AchievementService."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = AchievementService(self.db)

    def test_list_all(self):
        self.db.list_achievements.return_value = [{"id": "first"}]
        assert self.service.list_all() == [{"id": "first"}]

    def test_unlocked_count(self):
        self.db.unlocked_achievements_count.return_value = 5
        assert self.service.unlocked_count() == 5

    def test_update_progress_no_unlock(self):
        self.db.update_achievement_progress.return_value = False
        result = self.service.update_progress("id", 3)
        assert result is False

    def test_update_progress_with_unlock(self):
        self.db.update_achievement_progress.return_value = True
        self.db.fetchone.return_value = ("Title", "Description")
        with patch("app.services.base.event_bus") as mock_bus:
            result = self.service.update_progress("id", 10)
            assert result is True
            mock_bus.publish.assert_called_once()
            event = mock_bus.publish.call_args[0][0]
            assert event.title == "Title"

    def test_check_streak(self):
        self.db.check_streak_achievements.return_value = ["streak_3"]
        assert self.service.check_streak() == ["streak_3"]

    def test_check_completion(self):
        self.db.check_completion_achievements.return_value = []
        assert self.service.check_completion() == []

    def test_check_practice(self):
        self.db.check_practice_achievements.return_value = ["first_exercise"]
        assert self.service.check_practice() == ["first_exercise"]
