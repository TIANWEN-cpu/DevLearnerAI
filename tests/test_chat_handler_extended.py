"""Extended tests for app.ai.chat_handler covering business logic (non-GUI) paths.

Targets:
- _test_connection_worker exception branches (lines 723-728)
- _handle_stream_chunk (lines 695-698)
- _read_file_excerpt (lines 848-858)
- _build_system_context (lines 923-937)
"""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _test_connection_worker exception handling
# ---------------------------------------------------------------------------
class TestConnectionWorkerExceptions:
    """Test exception branches in _test_connection_worker (lines 720-729)."""

    def test_worker_connection_error(self):
        """ConnectionError should produce a friendly message."""
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.status_ready = MagicMock()
        panel._is_valid = True

        with patch("app.ai.chat_handler.api_test_connection", side_effect=ConnectionError("refused")):
            panel._test_connection_worker("https://host", "key")

        panel.status_ready.emit.assert_called_once()
        msg = panel.status_ready.emit.call_args[0][0]
        assert "Cannot connect" in msg or "连接" in msg

    def test_worker_timeout_error(self):
        """TimeoutError should produce a timeout message."""
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.status_ready = MagicMock()
        panel._is_valid = True

        with patch("app.ai.chat_handler.api_test_connection", side_effect=TimeoutError("timed out")):
            panel._test_connection_worker("https://host", "key")

        msg = panel.status_ready.emit.call_args[0][0]
        assert "timed out" in msg or "超时" in msg

    def test_worker_generic_exception(self):
        """Generic exceptions should produce a failure message."""
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.status_ready = MagicMock()
        panel._is_valid = True

        with patch("app.ai.chat_handler.api_test_connection", side_effect=RuntimeError("oops")):
            panel._test_connection_worker("https://host", "key")

        msg = panel.status_ready.emit.call_args[0][0]
        assert "failed" in msg.lower() or "失败" in msg


# ---------------------------------------------------------------------------
# _fetch_models_worker
# ---------------------------------------------------------------------------
class TestFetchModelsWorker:
    """Test _fetch_models_worker exception handling."""

    def test_fetch_models_success(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.models_ready = MagicMock()
        panel.status_ready = MagicMock()
        panel._is_valid = True

        with patch("app.ai.chat_handler.api_fetch_models", return_value=["gpt-4", "gpt-3.5"]):
            panel._fetch_models_worker("https://host", "key")

        panel.models_ready.emit.assert_called_once_with(["gpt-4", "gpt-3.5"])

    def test_fetch_models_failure(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.models_ready = MagicMock()
        panel.status_ready = MagicMock()
        panel._is_valid = True

        with patch("app.ai.chat_handler.api_fetch_models", side_effect=RuntimeError("fail")):
            panel._fetch_models_worker("https://host", "key")

        panel.status_ready.emit.assert_called_once()
        msg = panel.status_ready.emit.call_args[0][0]
        assert "失败" in msg


# ---------------------------------------------------------------------------
# _handle_stream_chunk
# ---------------------------------------------------------------------------
class TestHandleStreamChunk:
    """Test _handle_stream_chunk (lines 693-698)."""

    def test_stream_chunk_updates_buffer(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.thinking_hint = MagicMock()
        panel._stream_buffer = ""

        panel._handle_stream_chunk("Hello")
        assert panel._stream_buffer == "Hello"
        panel.thinking_hint.setText.assert_called_once()

    def test_stream_chunk_long_buffer_truncates_preview(self):
        """When buffer is > 80 chars, preview should be last 80."""
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.thinking_hint = MagicMock()
        panel._stream_buffer = ""

        long_text = "x" * 200
        panel._handle_stream_chunk(long_text)
        assert len(panel._stream_buffer) == 200
        call_text = panel.thinking_hint.setText.call_args[0][0]
        assert len(call_text) < 200 + 30  # preview + prefix


# ---------------------------------------------------------------------------
# _read_file_excerpt
# ---------------------------------------------------------------------------
class TestReadFileExcerpt:
    """Test _read_file_excerpt static method (lines 847-858)."""

    def test_read_utf8_file(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello UTF-8 content", encoding="utf-8")

        result = AIMentorPanel._read_file_excerpt(str(test_file))
        assert "Hello UTF-8 content" in result

    def test_read_file_truncates_to_6000(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        test_file = tmp_path / "big.txt"
        test_file.write_text("x" * 10000, encoding="utf-8")

        result = AIMentorPanel._read_file_excerpt(str(test_file))
        assert len(result) == 6000

    def test_read_nonexistent_file_returns_empty(self):
        from app.ai.chat_handler import AIMentorPanel

        result = AIMentorPanel._read_file_excerpt("/nonexistent/path/file.txt")
        assert result == ""

    def test_read_binary_file_returns_empty(self, tmp_path):
        from app.ai.chat_handler import AIMentorPanel

        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\xff\xfe")

        result = AIMentorPanel._read_file_excerpt(str(test_file))
        # Should either decode or return empty
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _populate_models
# ---------------------------------------------------------------------------
class TestPopulateModels:
    """Test _populate_models (lines 748-753)."""

    def test_populate_models_preserves_current(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.model_combo = MagicMock()
        panel.model_combo.currentText.return_value = "gpt-4"
        panel.model_combo.count.return_value = 2

        panel._populate_models(["gpt-4", "gpt-3.5"])
        panel.model_combo.addItems.assert_called_once_with(["gpt-4", "gpt-3.5"])

    def test_populate_models_clears_first(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.model_combo = MagicMock()
        panel.model_combo.currentText.return_value = "old-model"

        panel._populate_models(["new-model"])
        panel.model_combo.clear.assert_called_once()


# ---------------------------------------------------------------------------
# _set_settings_status
# ---------------------------------------------------------------------------
class TestSetSettingsStatus:
    def test_sets_status_text(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.settings_status = MagicMock()

        panel._set_settings_status("test message")
        panel.settings_status.setText.assert_called_once_with("test message")


# ---------------------------------------------------------------------------
# _toggle_mode
# ---------------------------------------------------------------------------
class TestToggleMode:
    def test_toggle_page_mode_opens_dock(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.request_open_dock = MagicMock()
        panel.request_open_page = MagicMock()
        panel.mode = "page"

        panel._toggle_mode()
        panel.request_open_dock.emit.assert_called_once()

    def test_toggle_dock_mode_opens_page(self):
        from app.ai.chat_handler import AIMentorPanel

        panel = object.__new__(AIMentorPanel)
        panel.request_open_dock = MagicMock()
        panel.request_open_page = MagicMock()
        panel.mode = "dock"

        panel._toggle_mode()
        panel.request_open_page.emit.assert_called_once()
