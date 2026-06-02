"""Tests for app.ai.chat_handler -- AIMentorPanel and AIMentorDock.

Requires a QApplication instance (created in fixture).
Mocks AppDatabase and ContentService to avoid real DB/filesystem.
"""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# QApplication fixture (required for all QWidget tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def qapp():
    """Create a QApplication for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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
def panel(qapp, mock_db, mock_content_service):
    """Create an AIMentorPanel in 'page' mode with mocked dependencies."""
    from app.ai.chat_handler import AIMentorPanel

    p = AIMentorPanel(mock_db, mock_content_service, mode="page")
    return p


@pytest.fixture
def dock_panel(qapp, mock_db, mock_content_service):
    """Create an AIMentorPanel in 'dock' mode."""
    from app.ai.chat_handler import AIMentorPanel

    p = AIMentorPanel(mock_db, mock_content_service, mode="dock")
    return p


# ---------------------------------------------------------------------------
# _card_style helper
# ---------------------------------------------------------------------------
class TestCardStyle:
    """Test the _card_style helper function."""

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
    """Test panel creation and initial state."""

    def test_panel_created_page_mode(self, panel):
        assert panel.mode == "page"
        assert panel.current_session_id is None
        assert panel._request_in_flight is False
        assert panel._is_valid is True

    def test_panel_created_dock_mode(self, dock_panel):
        assert dock_panel.mode == "dock"

    def test_panel_has_ui_elements(self, panel):
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
    """Test legacy message cleanup."""

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
    """Test session snapshot generation."""

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
        long_msg = "x" * 200
        mock_db.load_mentor_messages.return_value = [
            ("user", long_msg, "2025-01-01"),
        ]
        snapshot = panel._session_snapshot(1)
        assert len(snapshot["preview"]) <= 80
        assert "..." in snapshot["preview"]


# ---------------------------------------------------------------------------
# _set_pending
# ---------------------------------------------------------------------------
class TestSetPending:
    """Test pending state management."""

    def test_set_pending_true(self, panel):
        panel._set_pending(True)
        assert panel._request_in_flight is True
        assert not panel.send_btn.isEnabled()
        assert "思考中" in panel.send_btn.text()
        assert panel.thinking_hint.isVisible()

    def test_set_pending_false(self, panel):
        panel._set_pending(True)
        panel._set_pending(False)
        assert panel._request_in_flight is False
        assert panel.send_btn.isEnabled()
        assert panel.send_btn.text() == "发送"
        assert not panel.thinking_hint.isVisible()


# ---------------------------------------------------------------------------
# _set_settings_status
# ---------------------------------------------------------------------------
class TestSetSettingsStatus:
    """Test settings status label update."""

    def test_sets_text(self, panel):
        panel._set_settings_status("测试消息")
        assert panel.settings_status.text() == "测试消息"


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------
class TestSaveConfig:
    """Test config saving."""

    def test_saves_to_db(self, panel, mock_db):
        panel.host_input.setText("https://api.test.com/v1")
        panel.key_input.setText("sk-abc")
        panel.model_combo.addItem("gpt-4")
        panel.model_combo.setCurrentText("gpt-4")
        panel.save_config()
        mock_db.save_api_config.assert_called_once()
        assert "已保存" in panel.settings_status.text()


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------
class TestTestConnection:
    """Test connection testing flow."""

    def test_empty_host_shows_error(self, panel):
        panel.host_input.setText("")
        panel.key_input.setText("")
        panel.test_connection()
        assert "请先填写" in panel.settings_status.text()

    def test_empty_key_shows_error(self, panel):
        panel.host_input.setText("https://api.test.com")
        panel.key_input.setText("")
        panel.test_connection()
        assert "请先填写" in panel.settings_status.text()


# ---------------------------------------------------------------------------
# fetch_models
# ---------------------------------------------------------------------------
class TestFetchModels:
    """Test model fetching flow."""

    def test_empty_host_shows_error(self, panel):
        panel.host_input.setText("")
        panel.key_input.setText("")
        panel.fetch_models()
        assert "请先填写" in panel.settings_status.text()

    def test_empty_key_shows_error(self, panel):
        panel.host_input.setText("https://api.test.com")
        panel.key_input.setText("")
        panel.fetch_models()
        assert "请先填写" in panel.settings_status.text()


# ---------------------------------------------------------------------------
# _populate_models
# ---------------------------------------------------------------------------
class TestPopulateModels:
    """Test model list population."""

    def test_populates_models(self, panel):
        panel._populate_models(["gpt-4", "gpt-3.5-turbo"])
        assert panel.model_combo.count() == 2
        assert panel.model_combo.itemText(0) == "gpt-4"

    def test_preserves_current_selection(self, panel):
        panel.model_combo.addItem("gpt-4")
        panel.model_combo.setCurrentText("gpt-4")
        panel._populate_models(["gpt-4", "gpt-3.5-turbo"])
        assert panel.model_combo.currentText() == "gpt-4"

    def test_clears_old_models(self, panel):
        panel.model_combo.addItem("old-model")
        panel._populate_models(["new-model"])
        assert panel.model_combo.count() == 1
        assert panel.model_combo.itemText(0) == "new-model"


# ---------------------------------------------------------------------------
# _toggle_mode
# ---------------------------------------------------------------------------
class TestToggleMode:
    """Test mode toggle signals."""

    def test_page_mode_emits_open_dock(self, panel):
        with patch.object(panel, "request_open_dock") as mock_signal:
            panel._toggle_mode()
            mock_signal.emit.assert_called_once()

    def test_dock_mode_emits_open_page(self, dock_panel):
        with patch.object(dock_panel, "request_open_page") as mock_signal:
            dock_panel._toggle_mode()
            mock_signal.emit.assert_called_once()


# ---------------------------------------------------------------------------
# refresh_shared_state
# ---------------------------------------------------------------------------
class TestRefreshSharedState:
    """Test shared state refresh from DB."""

    def test_loads_config(self, panel, mock_db):
        panel.refresh_shared_state()
        assert panel.host_input.text() == "https://api.example.com/v1"
        assert panel.key_input.text() == "sk-test"

    def test_loads_workspace_flags(self, panel, mock_db):
        panel.refresh_shared_state()
        assert panel.base_cb.isChecked()
        assert panel.personal_cb.isChecked()
        assert panel.custom_cb.isChecked()


# ---------------------------------------------------------------------------
# _ensure_sessions
# ---------------------------------------------------------------------------
class TestEnsureSessions:
    """Test session creation when none exist."""

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
    """Test message rendering."""

    def test_no_session_clears_chat(self, panel):
        panel.current_session_id = None
        panel._render_messages()
        # Should not crash

    def test_empty_messages_shows_placeholder(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = []
        panel._render_messages()
        html = panel.chat.toHtml()
        assert "建议按主题拆分" in html or "保留你和 AI 的对话" in html

    def test_renders_user_message(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = [
            ("user", "hello", "2025-01-01"),
        ]
        panel._render_messages()
        html = panel.chat.toHtml()
        assert "hello" in html

    def test_renders_multiple_messages(self, panel, mock_db):
        panel.current_session_id = 1
        mock_db.load_mentor_messages.return_value = [
            ("user", "question", "2025-01-01"),
            ("assistant", "answer", "2025-01-01"),
        ]
        panel._render_messages()
        html = panel.chat.toHtml()
        assert "question" in html
        assert "answer" in html


# ---------------------------------------------------------------------------
# _handle_response_ready
# ---------------------------------------------------------------------------
class TestHandleResponseReady:
    """Test response ready handler."""

    def test_reloads_and_renders(self, panel, mock_db):
        panel.current_session_id = 1
        panel._set_pending(True)
        panel._handle_response_ready(1)
        assert not panel._request_in_flight

    def test_different_session_id_still_reloads(self, panel, mock_db):
        panel.current_session_id = 1
        panel._handle_response_ready(2)
        # Should not crash; just reloads sessions


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------
class TestSendMessage:
    """Test message sending flow."""

    def test_no_session_does_nothing(self, panel):
        panel.current_session_id = None
        panel.input.setText("hello")
        panel.send_message()
        # Should not crash

    def test_empty_message_does_nothing(self, panel):
        panel.current_session_id = 1
        panel.input.setText("")
        panel.send_message()
        # Should not crash

    def test_already_in_flight_does_nothing(self, panel, mock_db):
        panel.current_session_id = 1
        panel.input.setText("hello")
        panel._request_in_flight = True
        panel.send_message()
        mock_db.append_mentor_message.assert_not_called()

    def test_no_config_shows_message(self, panel, mock_db):
        panel.current_session_id = 1
        panel.input.setText("hello")
        panel.host_input.setText("")
        panel.key_input.setText("")
        panel.send_message()
        # Should append a message about missing config
        calls = mock_db.append_mentor_message.call_args_list
        assert any("配置" in str(c) for c in calls)

    def test_valid_config_starts_thread(self, panel, mock_db):
        panel.current_session_id = 1
        panel.input.setText("hello")
        panel.host_input.setText("https://api.example.com/v1")
        panel.key_input.setText("sk-test")
        panel.model_combo.addItem("gpt-4")
        panel.model_combo.setCurrentText("gpt-4")
        with patch("app.ai.chat_handler.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            panel.send_message()
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()


# ---------------------------------------------------------------------------
# _knowledge_overview_text
# ---------------------------------------------------------------------------
class TestKnowledgeOverviewText:
    """Test knowledge overview text generation."""

    def test_all_enabled(self, panel):
        panel.base_cb.setChecked(True)
        panel.personal_cb.setChecked(True)
        panel.custom_cb.setChecked(True)
        text = panel._knowledge_overview_text()
        assert "基础知识库" in text

    def test_none_enabled(self, panel):
        panel.base_cb.setChecked(False)
        panel.personal_cb.setChecked(False)
        panel.custom_cb.setChecked(False)
        text = panel._knowledge_overview_text()
        assert "没有启用" in text

    def test_only_base(self, panel):
        panel.base_cb.setChecked(True)
        panel.personal_cb.setChecked(False)
        panel.custom_cb.setChecked(False)
        text = panel._knowledge_overview_text()
        assert "基础知识库" in text
        assert "个性知识库" not in text


# ---------------------------------------------------------------------------
# _base_knowledge_text
# ---------------------------------------------------------------------------
class TestBaseKnowledgeText:
    """Test base knowledge text from content service."""

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
        assert "Basics" in text

    def test_empty_tracks(self, panel, mock_content_service):
        mock_content_service.tracks = []
        text = panel._base_knowledge_text()
        assert "基础知识库" in text


# ---------------------------------------------------------------------------
# _personal_knowledge_text
# ---------------------------------------------------------------------------
class TestPersonalKnowledgeText:
    """Test personal knowledge text generation."""

    def test_generates_stats(self, panel, mock_db):
        text = panel._personal_knowledge_text()
        assert "已完成课程数" in text
        assert "练习平均分" in text
        assert "连续学习天数" in text

    def test_with_recent_attempts(self, panel, mock_db):
        mock_db.fetchall.return_value = [
            ("exercise1", 85, True, "2025-01-01"),
            ("exercise2", 60, False, "2025-01-02"),
        ]
        text = panel._personal_knowledge_text()
        assert "最近练习记录" in text


# ---------------------------------------------------------------------------
# _custom_knowledge_text
# ---------------------------------------------------------------------------
class TestCustomKnowledgeText:
    """Test custom knowledge text generation."""

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
    """Test system context building."""

    def test_contains_base_instructions(self, panel):
        ctx = panel._build_system_context()
        assert "DevLearner" in ctx
        assert "AI 助手" in ctx

    def test_includes_knowledge_when_enabled(self, panel):
        panel.base_cb.setChecked(True)
        panel.personal_cb.setChecked(True)
        panel.custom_cb.setChecked(True)
        ctx = panel._build_system_context()
        assert "基础知识库" in ctx


# ---------------------------------------------------------------------------
# _seed_prompt
# ---------------------------------------------------------------------------
class TestSeedPrompt:
    """Test prompt seeding."""

    def test_sets_input_text(self, panel):
        panel._seed_prompt("test prompt")
        assert panel.input.text() == "test prompt"


# ---------------------------------------------------------------------------
# _read_file_excerpt (static method)
# ---------------------------------------------------------------------------
class TestReadFileExcerpt:
    """Test file excerpt reading."""

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
    """Test connection worker thread callback."""

    def test_emits_status(self, panel):
        with patch("app.ai.chat_handler.api_test_connection", return_value="连接成功"):
            panel._test_connection_worker("https://api.example.com", "sk-test")


# ---------------------------------------------------------------------------
# _fetch_models_worker
# ---------------------------------------------------------------------------
class TestFetchModelsWorker:
    """Test fetch models worker thread callback."""

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
    """Test chat worker thread callback."""

    def test_success(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = [("user", "hi", "2025-01-01")]
        with patch("app.ai.chat_handler.api_send_chat", return_value="hello!"):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        mock_db.append_mentor_message.assert_called()

    def test_value_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        with patch("app.ai.chat_handler.api_send_chat", side_effect=ValueError("bad")):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        # Should still append error message
        calls = mock_db.append_mentor_message.call_args_list
        assert any("响应解析失败" in str(c) for c in calls)

    def test_http_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        exc = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, BytesIO(b'{"error":{"message":"oops"}}'))
        with patch("app.ai.chat_handler.api_send_chat", side_effect=exc):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        calls = mock_db.append_mentor_message.call_args_list
        assert any("HTTP 500" in str(c) for c in calls)

    def test_http_error_unreadable_body(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        exc = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, BytesIO(b"bad json"))
        with patch("app.ai.chat_handler.api_send_chat", side_effect=exc):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        calls = mock_db.append_mentor_message.call_args_list
        assert any("HTTP 500" in str(c) for c in calls)

    def test_unexpected_error(self, panel, mock_db):
        mock_db.load_mentor_messages.return_value = []
        with patch("app.ai.chat_handler.api_send_chat", side_effect=RuntimeError("boom")):
            panel._chat_worker("https://api.example.com", "sk-test", "gpt-4", "system", 1)
        calls = mock_db.append_mentor_message.call_args_list
        assert any("连接失败" in str(c) for c in calls)


# ---------------------------------------------------------------------------
# AIMentorDock
# ---------------------------------------------------------------------------
class TestAIMentorDock:
    """Test AIMentorDock wrapper."""

    def test_dock_created(self, qapp, mock_db, mock_content_service):
        from app.ai.chat_handler import AIMentorDock

        dock = AIMentorDock(mock_db, mock_content_service)
        assert dock.windowTitle() == "AI 助手"
        assert dock.panel is not None

    def test_dock_input_property(self, qapp, mock_db, mock_content_service):
        from app.ai.chat_handler import AIMentorDock

        dock = AIMentorDock(mock_db, mock_content_service)
        assert dock.input is dock.panel.input


# Need to import BytesIO for HTTPError mock
from io import BytesIO
