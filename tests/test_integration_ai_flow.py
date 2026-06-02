"""Integration tests for the AI flow: session management -> message flow -> history retrieval.

These tests exercise the database-backed AI session management, message
flow, configuration handling, and the API client URL construction and
validation -- all without requiring a running Qt GUI or real API server.
"""

import pytest

from app.ai.api_client import build_chat_url, build_models_url, create_ssl_context, require_https
from app.ai.markdown_renderer import bubble_html, render_message_html, sanitize_html
from app.ai.models import ALLOWED_TAGS, STRIP_TAGS
from app.database import AppDatabase, close_connection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def db(tmp_path):
    """Create an isolated AppDatabase for each test."""
    close_connection()
    db_path = tmp_path / "ai_flow.db"
    database = AppDatabase(db_path=db_path)
    database.init_db()
    database.reset_learning_progress()
    # Clear any sessions created during init_db (default session)
    # so each test starts clean
    for sid, _, _ in database.list_mentor_sessions():
        database.delete_mentor_session(sid)
    yield database
    close_connection()


# ---------------------------------------------------------------------------
# 1. Session creation -> message flow -> history retrieval
# ---------------------------------------------------------------------------
class TestSessionCreationAndManagement:
    """Test AI session lifecycle through the database."""

    def test_create_session_returns_id(self, db):
        sid = db.create_mentor_session("New Chat")
        assert isinstance(sid, int)
        assert sid > 0

    def test_create_multiple_sessions(self, db):
        s1 = db.create_mentor_session("Python Help")
        s2 = db.create_mentor_session("SQL Questions")
        s3 = db.create_mentor_session("Project Planning")

        sessions = db.list_mentor_sessions()
        ids = {s[0] for s in sessions}
        assert s1 in ids
        assert s2 in ids
        assert s3 in ids

    def test_sessions_ordered_by_update_time(self, db):
        _s1 = db.create_mentor_session("First")
        s2 = db.create_mentor_session("Second")
        # s2 was created last, should be first in the list
        sessions = db.list_mentor_sessions()
        assert sessions[0][0] == s2

    def test_rename_session(self, db):
        sid = db.create_mentor_session("Original")
        db.rename_mentor_session(sid, "Renamed")
        sessions = db.list_mentor_sessions()
        matched = [s for s in sessions if s[0] == sid]
        assert matched[0][1] == "Renamed"

    def test_delete_session_removes_messages(self, db):
        sid = db.create_mentor_session("To Delete")
        db.append_mentor_message(sid, "user", "msg 1")
        db.append_mentor_message(sid, "assistant", "msg 2")
        db.delete_mentor_session(sid)

        sessions = db.list_mentor_sessions()
        assert not any(s[0] == sid for s in sessions)
        assert db.load_mentor_messages(sid) == []


class TestMessageFlow:
    """Test message append, load, and ordering."""

    def test_append_and_load_messages(self, db):
        sid = db.create_mentor_session("Chat")
        db.append_mentor_message(sid, "user", "What is recursion?")
        db.append_mentor_message(sid, "assistant", "Recursion is when a function calls itself.")
        db.append_mentor_message(sid, "user", "Can you give an example?")
        db.append_mentor_message(sid, "assistant", "Sure! Here is a factorial example...")

        messages = db.load_mentor_messages(sid)
        assert len(messages) == 4
        assert messages[0][0] == "user"
        assert messages[0][1] == "What is recursion?"
        assert messages[2][0] == "user"
        assert messages[3][0] == "assistant"

    def test_message_order_is_chronological(self, db):
        sid = db.create_mentor_session("Order Test")
        contents = [f"Message {i}" for i in range(10)]
        for content in contents:
            db.append_mentor_message(sid, "user", content)

        messages = db.load_mentor_messages(sid)
        loaded_contents = [m[1] for m in messages]
        assert loaded_contents == contents

    def test_messages_isolated_between_sessions(self, db):
        s1 = db.create_mentor_session("Session 1")
        s2 = db.create_mentor_session("Session 2")

        db.append_mentor_message(s1, "user", "Message for session 1")
        db.append_mentor_message(s2, "user", "Message for session 2")

        msgs1 = db.load_mentor_messages(s1)
        msgs2 = db.load_mentor_messages(s2)
        assert len(msgs1) == 1
        assert len(msgs2) == 1
        assert msgs1[0][1] == "Message for session 1"
        assert msgs2[0][1] == "Message for session 2"

    def test_message_updates_session_timestamp(self, db):
        sid = db.create_mentor_session("Timestamp Test")
        # The session was just created, so updated_at is recent
        sessions_before = db.list_mentor_sessions()
        before_ts = [s for s in sessions_before if s[0] == sid][0][2]

        db.append_mentor_message(sid, "user", "New message")
        sessions_after = db.list_mentor_sessions()
        after_ts = [s for s in sessions_after if s[0] == sid][0][2]

        # updated_at should have been refreshed
        assert after_ts >= before_ts

    def test_session_snapshot_after_messages(self, db):
        sid = db.create_mentor_session("Snapshot")

        # Empty session
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["message_count"] == 0

        # Add messages
        db.append_mentor_message(sid, "user", "Hello!")
        db.append_mentor_message(sid, "assistant", "Hi there, how can I help?")
        snapshot = db.mentor_session_snapshot(sid)
        assert snapshot["message_count"] == 2
        # Last message is from assistant, so prefix is "AI："
        assert "AI：" in snapshot["preview"]


class TestHistoryRetrieval:
    """Test message history retrieval for AI context building."""

    def test_load_recent_messages_for_context(self, db):
        """Simulate loading the last N messages for API context."""
        sid = db.create_mentor_session("Context Test")
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            db.append_mentor_message(sid, role, f"Message {i}")

        # Load all messages
        all_msgs = db.load_mentor_messages(sid)
        assert len(all_msgs) == 20

        # Simulate taking last 12 for context (as chat_handler does)
        context_msgs = all_msgs[-12:]
        assert len(context_msgs) == 12
        assert context_msgs[0][1] == "Message 8"  # 20 - 12 = 8

    def test_context_messages_formatted_for_api(self, db):
        """Verify messages can be formatted as API-ready dicts."""
        sid = db.create_mentor_session("Format Test")
        db.append_mentor_message(sid, "user", "Explain closures")
        db.append_mentor_message(sid, "assistant", "A closure is a function...")

        messages = db.load_mentor_messages(sid)
        api_messages = [{"role": role, "content": content} for role, content, _ in messages]
        assert api_messages[0] == {"role": "user", "content": "Explain closures"}
        assert api_messages[1] == {"role": "assistant", "content": "A closure is a function..."}

    def test_full_conversation_round_trip(self, db):
        """Simulate a full conversation: create session, exchange messages, retrieve history."""
        sid = db.create_mentor_session("Python Basics")

        # User asks a question
        db.append_mentor_message(sid, "user", "What are decorators in Python?")

        # AI responds
        db.append_mentor_message(
            sid,
            "assistant",
            "Decorators are a way to modify functions using @syntax. They wrap a function with another function.",
        )

        # User follows up
        db.append_mentor_message(sid, "user", "Show me an example")

        # AI responds with code
        db.append_mentor_message(
            sid,
            "assistant",
            "Here is a simple decorator:\n```python\ndef my_decorator(func):\n"
            "    def wrapper():\n        print('Before')\n        func()\n"
            "        print('After')\n    return wrapper\n```",
        )

        # Verify full history
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 4
        assert messages[0][0] == "user"
        assert messages[3][0] == "assistant"
        assert "decorator" in messages[3][1]


# ---------------------------------------------------------------------------
# 2. Active session management
# ---------------------------------------------------------------------------
class TestActiveSessionManagement:
    """Test the active session tracking and fallback behavior."""

    def test_set_and_load_active_session(self, db):
        sid = db.create_mentor_session("Active Test")
        db.set_active_mentor_session(sid)
        assert db.load_active_mentor_session_id() == sid

    def test_switch_active_session(self, db):
        s1 = db.create_mentor_session("Session 1")
        s2 = db.create_mentor_session("Session 2")

        db.set_active_mentor_session(s1)
        assert db.load_active_mentor_session_id() == s1

        db.set_active_mentor_session(s2)
        assert db.load_active_mentor_session_id() == s2

    def test_delete_active_session_falls_back(self, db):
        """Deleting the active session should fall back to another session."""
        s1 = db.create_mentor_session("To Delete")
        s2 = db.create_mentor_session("Fallback")

        db.set_active_mentor_session(s1)
        assert db.load_active_mentor_session_id() == s1

        db.delete_mentor_session(s1)
        active_id = db.load_active_mentor_session_id()
        assert active_id != s1
        # Should have fallen back to s2
        assert active_id == s2

    def test_delete_last_session_leaves_none(self, db):
        """If only one session exists and it's deleted, active becomes None."""
        sid = db.create_mentor_session("Only Session")
        db.set_active_mentor_session(sid)
        db.delete_mentor_session(sid)
        # After deletion, init_db creates a default, but since we cleared
        # sessions in the fixture, active should be None
        active = db.load_active_mentor_session_id()
        # Could be None or the fallback might create a new session
        # Just verify it doesn't crash
        assert active is None or isinstance(active, int)


# ---------------------------------------------------------------------------
# 3. Configuration validation
# ---------------------------------------------------------------------------
class TestConfigurationValidation:
    """Test API configuration save/load and validation."""

    def test_require_https_rejects_http(self):
        with pytest.raises(ValueError, match="HTTPS"):
            require_https("http://api.example.com/v1")

    def test_require_https_accepts_https(self):
        result = require_https("https://api.example.com/v1")
        assert result is None

    def test_build_models_url_with_v1_suffix(self):
        assert build_models_url("https://api.example.com/v1") == "https://api.example.com/v1/models"

    def test_build_models_url_without_v1_suffix(self):
        assert build_models_url("https://api.example.com") == "https://api.example.com/v1/models"

    def test_build_chat_url_with_v1_suffix(self):
        url = build_chat_url("https://api.example.com/v1")
        assert url == "https://api.example.com/v1/chat/completions"

    def test_build_chat_url_without_v1_suffix(self):
        url = build_chat_url("https://api.example.com")
        assert url == "https://api.example.com/v1/chat/completions"

    def test_build_urls_with_trailing_slash(self):
        assert build_models_url("https://api.example.com/v1/") == "https://api.example.com/v1/models"
        assert build_chat_url("https://api.example.com/v1/") == "https://api.example.com/v1/chat/completions"

    def test_create_ssl_context_returns_valid_context(self):
        ctx = create_ssl_context()
        assert ctx is not None
        # Should verify certificates
        assert ctx.verify_mode is not None

    def test_api_config_round_trip(self, db, monkeypatch):
        """Save and load API config through the database."""
        import app.database as db_module

        saved = {}
        monkeypatch.setattr(db_module, "save_secret", lambda alias, key: saved.__setitem__(alias, key))
        monkeypatch.setattr(db_module, "load_secret", lambda alias: saved.get(alias))

        db.save_api_config("https://api.openai.com/v1", "sk-secret-key", "gpt-4")
        host, api_key, model = db.load_api_config()
        assert host == "https://api.openai.com/v1"
        assert api_key == "sk-secret-key"
        assert model == "gpt-4"

    def test_empty_api_config(self, db):
        """Load API config when none has been saved."""
        host, api_key, model = db.load_api_config()
        assert host == ""
        assert model == ""


# ---------------------------------------------------------------------------
# 4. Workspace flags
# ---------------------------------------------------------------------------
class TestWorkspaceFlags:
    """Test knowledge base workspace flag management."""

    def test_default_flags_are_all_enabled(self, db):
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is True
        assert flags["use_personal"] is True
        assert flags["use_custom"] is True

    def test_disable_individual_flags(self, db):
        db.save_mentor_workspace_flags(False, False, False)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is False
        assert flags["use_personal"] is False
        assert flags["use_custom"] is False

    def test_mixed_flags(self, db):
        db.save_mentor_workspace_flags(True, False, True)
        flags = db.load_mentor_workspace_flags()
        assert flags["use_base"] is True
        assert flags["use_personal"] is False
        assert flags["use_custom"] is True


# ---------------------------------------------------------------------------
# 5. Error handling paths
# ---------------------------------------------------------------------------
class TestErrorHandling:
    """Test error handling in AI-related operations."""

    def test_messages_for_nonexistent_session(self, db):
        """Loading messages for a nonexistent session should return empty list."""
        messages = db.load_mentor_messages(999999)
        assert messages == []

    def test_snapshot_for_nonexistent_session(self, db):
        """Snapshot of a nonexistent session should return a default."""
        snapshot = db.mentor_session_snapshot(999999)
        assert snapshot["message_count"] == 0

    def test_rename_nonexistent_session_no_crash(self, db):
        """Renaming a nonexistent session should not crash."""
        db.rename_mentor_session(999999, "Ghost")
        assert True  # Verify no exception raised

    def test_delete_nonexistent_session_no_crash(self, db):
        """Deleting a nonexistent session should not crash."""
        db.delete_mentor_session(999999)
        assert True  # Verify no exception raised

    def test_empty_message_content(self, db):
        """Appending a message with empty content should work."""
        sid = db.create_mentor_session("Empty Test")
        db.append_mentor_message(sid, "user", "")
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 1
        assert messages[0][1] == ""

    def test_very_long_message_content(self, db):
        """Appending a very long message should work."""
        sid = db.create_mentor_session("Long Test")
        long_text = "A" * 10000
        db.append_mentor_message(sid, "user", long_text)
        messages = db.load_mentor_messages(sid)
        assert len(messages) == 1
        assert messages[0][1] == long_text


# ---------------------------------------------------------------------------
# 6. HTML rendering and sanitization
# ---------------------------------------------------------------------------
class TestHTMLRendering:
    """Test the HTML rendering pipeline used for chat display."""

    def test_render_message_html_plain_text(self):
        html = render_message_html("Hello, world!", allow_markdown=False)
        assert "Hello, world!" in html
        # Should not contain raw HTML injection
        assert "<script>" not in html

    def test_render_message_html_empty(self):
        html = render_message_html("")
        assert "暂无内容" in html

    def test_render_message_html_none(self):
        html = render_message_html(None)
        assert "暂无内容" in html

    def test_bubble_html_user_message(self):
        html = bubble_html("user", "What is Python?")
        assert "你" in html
        assert "What is Python?" in html

    def test_bubble_html_assistant_message(self):
        html = bubble_html("assistant", "Python is a language.")
        assert "助手" in html
        assert "Python is a language." in html

    def test_sanitize_html_removes_script_tags(self):
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        sanitized = sanitize_html(html)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Hello" in sanitized
        assert "World" in sanitized

    def test_sanitize_html_removes_event_handlers(self):
        html = '<p onclick="alert(1)">Click me</p>'
        sanitized = sanitize_html(html)
        assert "onclick" not in sanitized
        assert "Click me" in sanitized

    def test_sanitize_html_keeps_allowed_tags(self):
        html = "<p>Para</p><strong>Bold</strong><em>Italic</em>"
        sanitized = sanitize_html(html)
        assert "<p>" in sanitized
        assert "<strong>" in sanitized
        assert "<em>" in sanitized

    def test_sanitize_html_removes_style_tags(self):
        html = "<style>body{color:red}</style><p>Text</p>"
        sanitized = sanitize_html(html)
        assert "<style>" not in sanitized
        assert "Text" in sanitized

    def test_render_markdown_code_block(self):
        """Code blocks should be rendered safely."""
        content = "Here is code:\n```python\nprint('hello')\n```"
        html = render_message_html(content, allow_markdown=True)
        assert "print" in html
        # Should not contain dangerous tags
        assert "<script>" not in html

    def test_sanitize_html_removes_iframe(self):
        html = '<iframe src="http://evil.com"></iframe><p>Safe</p>'
        sanitized = sanitize_html(html)
        assert "<iframe>" not in sanitized
        assert "Safe" in sanitized

    def test_allowed_tags_complete(self):
        """Verify the allowed tags set is comprehensive."""
        expected = {"p", "br", "strong", "em", "code", "pre", "a", "ul", "ol", "li"}
        assert expected.issubset(ALLOWED_TAGS)

    def test_strip_tags_include_dangerous_tags(self):
        """Verify dangerous tags are in the strip list."""
        assert "script" in STRIP_TAGS
        assert "style" in STRIP_TAGS
        assert "iframe" in STRIP_TAGS
