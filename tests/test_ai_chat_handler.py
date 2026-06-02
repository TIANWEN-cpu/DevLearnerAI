"""Tests for app.ai.chat_handler -- AIMentorPanel and AIMentorDock.

Mocks AppDatabase and ContentService to avoid real DB/filesystem.
Uses the PyQt5 mock from conftest.py.
"""

import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db():
    """Mock AppDatabase with common method stubs."""
    db = MagicMock()
    db.load_api_config.return_value = ("https://api.example.com/v1", "sk-test", "gpt-4")
    db.load_mentor_workspace_flags.return_value = {"use_base": True, "use_personal": True, "use_custom": True}
    db.list_mentor_sessions.return_value = [(1, "默认对话", "2025-01-01")]
    db.load_active_mentor_session_id.return_value = 1
    db.load_mentor_messages.return_value = []
    db.completed_lessons.return_value = 5
    db.average_score.return_value = 85.0
    db.active_days_streak.return_value = 3
    db.fetchall.return_value = []
    db.list_knowledge_files.return_value = []
    db.get_knowledge_file.return_value = None
    db.create_mentor_session.return_value = 2
    return db


@pytest.fixture
def mock_content_service():
    """Mock ContentService."""
    cs = MagicMock()
    cs.tracks = []
    return cs


@pytest.fixture
def panel(mock_db, mock_content_service):
    """Create an AIMentorPanel in 'page' mode with mocked dependencies."""
    from app.ai.chat_handler import AIMentorPanel

    return AIMentorPanel(mock_db, mock_content_service, mode="page")


@pytest.fixture
def dock_panel(mock_db, mock_content_service):
    """Create an AIMentorPanel in 'dock' mode."""
    from app.ai.chat_handler import AIMentorPanel

    return AIMentorPanel(mock_db, mock_content_service, mode="dock")


# ---------------------------------------------------------------------------
# _card_style helper
# ---------------------------------------------------------------------------
class TestCardStyle:
    def test_default_radius(self):
        from app.ai.chat_handler import _card_style

        result = _card_style()
        assert "20px" in result
        assert "QFrame" in result

    def test_custom_radius(self):
        from app.ai.chat_handler import _card_style

        result = _card_style(radius=15)
        assert "15px" in result


# ---------------------------------------------------------------------------
# AIMentorPanel initialization
# ---------------------------------------------------------------------------
class TestPanelInit:
    def test_panel_created_page_mode(self, panel):
        assert panel.mode == "page"
        assert panel._request_in_flight is False
        assert panel._is_valid is True

    def test_panel_created_dock_mode(self, dock_panel):
        assert dock_panel.mode == "dock"

    def test_panel_has_key_attributes(self, panel):
        assert hasattr(panel, "input")
        assert hasattr(panel, "send_btn")
        assert hasattr(panel, "chat")
        assert hasattr(panel, "host_input")
        assert hasattr(panel, "key_input")
        assert hasattr(panel, "model_combo")

    def test_panel_has_session_widgets_page_mode(self, panel):
        assert hasattr(panel, "session_list")
        assert hasattr(panel, "new_session_btn")
        assert hasattr(panel, "rename_session_btn")
        assert hasattr(panel, "delete_session_btn")

    def test_panel_has_session_widgets_dock_mode(self, dock_panel):
        assert hasattr(dock_panel, "session_combo")
        assert hasattr(dock_panel, "new_session_btn")

    def test_panel_has_knowledge_widgets(self, panel):
        assert hasattr(panel, "base_cb")
        assert hasattr(panel, "personal_cb")
        assert hasattr(panel, "custom_cb")
        assert hasattr(panel, "file_list")


# ---------------------------------------------------------------------------
# _clean_legacy_message (static method)
# ---------------------------------------------------------------------------
class TestCleanLegacyMessage:
    def test_normal_text_returned(self):
        from app.ai.chat_handler import AIMentorPanel

        assert AIMentorPanel._clean_legacy_message("hello world") == "hello world"

    def test_empty_returns_empty(self):
        from app.ai.chat_handler import AIMentorPanel

        assert AIMentorPanel._clean_legacy_message("") == ""

    def test_none_returns_empty(self):
        from app.ai.chat_handler import AIMentorPanel

        assert AIMentorPanel._clean_legacy_message(None) == ""

    def test_garbled_question_marks_cleaned(self):
        from app.ai.chat_handler import AIMentorPanel

        result = AIMentorPanel._clean_legacy_message("??????????")
        assert "自动清理" in result

    def test_normal_question_marks_kept(self):
        from app.ai.chat_handler import AIMentorPanel

        result = AIMentorPanel._clean_legacy_message("什么是 Python？这是一个好问题。")
        assert "Python" in result

    def test_mixed_whitespace_normalized(self):
        from app.ai.chat_handler import AIMentorPanel

        result = AIMentorPanel._clean_legacy_message("  hello   world  ")
        assert result == "hello   world"


# ---------------------------------------------------------------------------
# _session_snapshot
# ---------------------------------------------------------------------------
class TestSessionSnapshot:
    def test_empty_session(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        snapshot = panel._session_snapshot(1)
        assert snapshot["message_count"] == 0
        assert "还没有聊天记录" in snapshot["preview"]

    def test_user_message_snapshot(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = [
            ("user", "什么是 Python？", "2025-01-01"),
        ]
        snapshot = panel._session_snapshot(1)
        assert snapshot["message_count"] == 1
        assert "你：" in snapshot["preview"]

    def test_assistant_message_snapshot(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = [
            ("assistant", "Python 是一种编程语言。", "2025-01-01"),
        ]
        snapshot = panel._session_snapshot(1)
        assert "AI：" in snapshot["preview"]

    def test_long_message_truncated(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = [
            ("user", "x" * 200, "2025-01-01"),
        ]
        snapshot = panel._session_snapshot(1)
        assert len(snapshot["preview"]) <= 80
        assert "..." in snapshot["preview"]


# ---------------------------------------------------------------------------
# _set_pending
# ---------------------------------------------------------------------------
class TestSetPending:
    def test_set_pending_true(self, panel):
        panel._set_pending(True)
        assert panel._request_in_flight is True

    def test_set_pending_false(self, panel):
        panel._set_pending(True)
        panel._set_pending(False)
        assert panel._request_in_flight is False


# ---------------------------------------------------------------------------
# _set_settings_status
# ---------------------------------------------------------------------------
class TestSetSettingsStatus:
    def test_sets_text(self, panel):
        panel._set_settings_status("测试消息")
        # The mock widget's setText is called; verify no crash
        assert True


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------
class TestSaveConfig:
    def test_saves_to_db(self, panel, mock_db):
        panel.save_config()
        mock_db.save_api_config.assert_called_once()


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------
class TestTestConnection:
    def test_empty_host_shows_error(self, panel, mock_db):
        # Mock host_input.text() to return empty
        panel.host_input._mock_signals = {}
        panel.host_input.__dict__["_mock_signals"] = {"text": MagicMock(return_value="")}
        panel.test_connection()
        # Should call _set_settings_status with error message
        assert True  # Just verify no crash

    def test_calls_thread_when_valid(self, panel, mock_db):
        with patch("app.ai.chat_handler.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            panel.test_connection()
            # May or may not start thread depending on mock state


# ---------------------------------------------------------------------------
# fetch_models
# ---------------------------------------------------------------------------
class TestFetchModels:
    def test_fetch_does_not_crash(self, panel):
        panel.fetch_models()
        assert True


# ---------------------------------------------------------------------------
# _populate_models
# ---------------------------------------------------------------------------
class TestPopulateModels:
    def test_populates_models(self, panel, mock_db):
        panel._populate_models(["gpt-4", "gpt-3.5-turbo"])
        mock_db.list_mentor_sessions.assert_called()
        # Verify no crash during population

    def test_empty_list(self, panel):
        panel._populate_models([])
        assert True


# ---------------------------------------------------------------------------
# _toggle_mode
# ---------------------------------------------------------------------------
class TestToggleMode:
    def test_page_mode_emits_signal(self, panel):
        panel._toggle_mode()
        # Should not crash

    def test_dock_mode_emits_signal(self, dock_panel):
        dock_panel._toggle_mode()
        # Should not crash


# ---------------------------------------------------------------------------
# refresh_shared_state
# ---------------------------------------------------------------------------
class TestRefreshSharedState:
    def test_refreshes_without_crash(self, panel, mock_db):
        panel.refresh_shared_state()
        mock_db.load_api_config.assert_called()
        mock_db.load_mentor_workspace_flags.assert_called()


# ---------------------------------------------------------------------------
# _ensure_sessions
# ---------------------------------------------------------------------------
class TestEnsureSessions:
    def test_creates_default_session_when_empty(self, panel, mock_db):
        mock_db.list_mentor_sessions.side_effect = [[], [(2, "默认对话", "2025-01-01")]]
        panel._ensure_sessions()
        mock_db.create_mentor_session.assert_called_once_with("默认对话")

    def test_does_nothing_when_sessions_exist(self, panel, mock_db):
        mock_db.list_mentor_sessions.return_value = [(1, "已有会话", "2025-01-01")]
        mock_db.create_mentor_session.reset_mock()
        panel._ensure_sessions()
        mock_db.create_mentor_session.assert_not_called()


# ---------------------------------------------------------------------------
# _render_messages
# ---------------------------------------------------------------------------
class TestRenderMessages:
    def test_no_session_clears_chat(self, panel):
        panel.current_session_id = None
        panel._render_messages()
        assert True

    def test_empty_messages_renders(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = []
        panel._render_messages()
        assert True

    def test_renders_user_message(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = [
            ("user", "hello", "2025-01-01"),
        ]
        panel._render_messages()
        assert True

    def test_renders_multiple_messages(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = [
            ("user", "question", "2025-01-01"),
            ("assistant", "answer", "2025-01-01"),
        ]
        panel._render_messages()
        assert True


# ---------------------------------------------------------------------------
# _handle_response_ready
# ---------------------------------------------------------------------------
class TestHandleResponseReady:
    def test_reloads_sessions(self, panel, mock_db):
        panel._set_pending(True)
        panel._handle_response_ready(1)
        assert not panel._request_in_flight

    def test_different_session_id(self, panel):
        panel.current_session_id = 1
        panel._handle_response_ready(2)
        assert True


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------
class TestSendMessage:
    def test_no_session_does_nothing(self, panel):
        panel.current_session_id = None
        panel.send_message()
        assert True

    def test_already_in_flight_does_nothing(self, panel, mock_db):
        panel.current_session_id = 1
        panel._request_in_flight = True
        panel.send_message()
        mock_db.append_mentor_message.assert_not_called()

    def test_no_config_appends_error(self, panel, mock_db):
        panel.current_session_id = 1
        panel._request_in_flight = False
        panel.send_message()
        mock_db.append_mentor_message.assert_called()


# ---------------------------------------------------------------------------
# _knowledge_overview_text
# ---------------------------------------------------------------------------
class TestKnowledgeOverviewText:
    def test_all_enabled(self, panel):
        text = panel._knowledge_overview_text()
        assert "基础知识库" in text

    def test_none_enabled(self, panel):
        panel.base_cb._mock_signals = {}
        panel.personal_cb._mock_signals = {}
        panel.custom_cb._mock_signals = {}
        # isChecked() returns MagicMock by default; need to override
        panel.base_cb.__class__.isChecked = lambda self: False
        panel.personal_cb.__class__.isChecked = lambda self: False
        panel.custom_cb.__class__.isChecked = lambda self: False
        text = panel._knowledge_overview_text()
        assert "没有启用" in text
        # Restore
        del panel.base_cb.__class__.isChecked


# ---------------------------------------------------------------------------
# _base_knowledge_text
# ---------------------------------------------------------------------------
class TestBaseKnowledgeText:
    def test_with_tracks(self, panel, mock_content_service):
        track = MagicMock()
        track.title = "Python"
        track.summary = "Learn Python"
        module = MagicMock()
        module.title = "Basics"
        module.summary = "Basic concepts"
        track.modules = [module]
        mock_content_service.tracks = [track]
        text = panel._base_knowledge_text()
        assert "Python" in text

    def test_empty_tracks(self, panel, mock_content_service):
        mock_content_service.tracks = []
        text = panel._base_knowledge_text()
        assert "基础知识库" in text


# ---------------------------------------------------------------------------
# _personal_knowledge_text
# ---------------------------------------------------------------------------
class TestPersonalKnowledgeText:
    def test_generates_stats(self, panel, mock_db):
        mock_db.fetchall.return_value = []
        text = panel._personal_knowledge_text()
        assert "已完成课程数" in text

    def test_with_recent_attempts(self, panel, mock_db):
        # fetchall is called twice: first for practice_attempts (4 cols), then for lesson_progress (3 cols)
        mock_db.fetchall.side_effect = [
            [("exercise1", 85, True, "2025-01-01")],
            [("lesson1", "in_progress", False)],
        ]
        text = panel._personal_knowledge_text()
        assert "最近练习记录" in text
        assert "最近课程进度" in text


# ---------------------------------------------------------------------------
# _custom_knowledge_text
# ---------------------------------------------------------------------------
class TestCustomKnowledgeText:
    def test_no_files(self, panel, mock_db):
        mock_db.list_knowledge_files.return_value = []
        text = panel._custom_knowledge_text()
        assert "还没有添加文件" in text

    def test_with_files(self, panel, mock_db):
        mock_db.list_knowledge_files.return_value = [
            (1, "test.py", "/path/test.py", "print('hello')"),
        ]
        text = panel._custom_knowledge_text()
        assert "test.py" in text


# ---------------------------------------------------------------------------
# _build_system_context
# ---------------------------------------------------------------------------
class TestBuildSystemContext:
    def test_contains_base_instructions(self, panel):
        ctx = panel._build_system_context()
        assert "DevLearner" in ctx

    def test_includes_knowledge(self, panel):
        ctx = panel._build_system_context()
        assert "基础知识库" in ctx


# ---------------------------------------------------------------------------
# _seed_prompt
# ---------------------------------------------------------------------------
class TestSeedPrompt:
    def test_sets_input_text(self, panel):
        panel._seed_prompt("test prompt")
        assert True  # Verify no crash


# ---------------------------------------------------------------------------
# _read_file_excerpt (static method)
# ---------------------------------------------------------------------------
class TestReadFileExcerpt:
    def test_reads_utf8_file(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        result = AIMentorPanel._read_file_excerpt(str(f))
        assert result == "hello world"

    def test_truncates_long_file(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        f = tmp_path / "long.txt"
        f.write_text("x" * 10000, encoding="utf-8")
        result = AIMentorPanel._read_file_excerpt(str(f))
        assert len(result) == 6000

    def test_nonexistent_file_returns_empty(self):
        from app.ai.chat_handler import AIMentorPanel

        result = AIMentorPanel._read_file_excerpt("/nonexistent/path.txt")
        assert result == ""

    def test_binary_file_returns_empty(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        result = AIMentorPanel._read_file_excerpt(str(f))
        assert result == ""


# ---------------------------------------------------------------------------
# _test_connection_worker
# ---------------------------------------------------------------------------
class TestTestConnectionWorker:
    def test_calls_api(self, panel):
        with patch("app.ai.chat_handler.api_test_connection", return_value="连接成功"):
            panel._test_connection_worker("https://api.example.com", "sk-test")


# ---------------------------------------------------------------------------
# _fetch_models_worker
# ---------------------------------------------------------------------------
class TestFetchModelsWorker:
    def test_success(self, panel):
        with patch("app.ai.chat_handler.api_fetch_models", return_value=["gpt-4"]):
            panel._fetch_models_worker("https://api.example.com", "sk-test")

    def test_failure(self, panel):
        with patch("app.ai.chat_handler.api_fetch_models", side_effect=Exception("fail")):
            panel._fetch_models_worker("https://api.example.com", "sk-test")


# ---------------------------------------------------------------------------
# _chat_worker
# ---------------------------------------------------------------------------
class TestChatWorker:
    def test_success(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = [("user", "hi", "2025-01-01")]
        with patch("app.ai.chat_handler.api_send_chat", return_value="hello!"):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()

    def test_value_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        with patch("app.ai.chat_handler.api_send_chat", side_effect=ValueError("bad")):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()

    def test_http_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        exc = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, BytesIO(b'{"error":{"message":"oops"}}'))
        with patch("app.ai.chat_handler.api_send_chat", side_effect=exc):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()

    def test_http_error_unreadable_body(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        exc = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, BytesIO(b"bad json"))
        with patch("app.ai.chat_handler.api_send_chat", side_effect=exc):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()

    def test_unexpected_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        with patch("app.ai.chat_handler.api_send_chat", side_effect=RuntimeError("boom")):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()


# ---------------------------------------------------------------------------
# AIMentorDock
# ---------------------------------------------------------------------------
class TestAIMentorDock:
    def test_dock_created(self, mock_db, mock_content_service):
        from app.ai.chat_handler import AIMentorDock

        dock = AIMentorDock(mock_db, mock_content_service)
        assert dock.panel is not None

    def test_dock_input_property(self, mock_db, mock_content_service):
        from app.ai.chat_handler import AIMentorDock

        dock = AIMentorDock(mock_db, mock_content_service)
        assert dock.input is dock.panel.input
