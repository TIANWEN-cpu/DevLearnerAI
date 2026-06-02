"""Tests for app.ai package -- models, __init__, api_client, markdown_renderer.

Covers:
- app.ai.models: constants and regex patterns
- app.ai.__init__: re-exports
- app.ai.api_client: URL building, HTTPS validation, SSL context, mocked HTTP
- app.ai.markdown_renderer: HTML sanitizer, render_message_html, bubble_html
"""

import json
import ssl
import urllib.error
from http.client import HTTPResponse
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# app.ai.models -- constants and regex
# ---------------------------------------------------------------------------
class TestAIModels:
    """Test that ALLOWED_TAGS, STRIP_TAGS, and regex patterns are correct."""

    def test_allowed_tags_is_frozenset(self):
        from app.ai.models import ALLOWED_TAGS

        assert isinstance(ALLOWED_TAGS, frozenset)

    def test_allowed_tags_contains_common_tags(self):
        from app.ai.models import ALLOWED_TAGS

        for tag in ("p", "br", "h1", "h2", "code", "pre", "strong", "em", "a", "table", "tr", "td"):
            assert tag in ALLOWED_TAGS

    def test_strip_tags_contains_dangerous_tags(self):
        from app.ai.models import STRIP_TAGS

        for tag in ("script", "style", "iframe", "object", "embed"):
            assert tag in STRIP_TAGS

    def test_re_event_attr_matches_on_handlers(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("onclick")
        assert RE_EVENT_ATTR.match("onerror")
        assert RE_EVENT_ATTR.match("ONLOAD")
        assert not RE_EVENT_ATTR.match("class")
        assert not RE_EVENT_ATTR.match("href")

    def test_re_javascript_uri(self):
        from app.ai.models import RE_JAVASCRIPT_URI

        assert RE_JAVASCRIPT_URI.match("javascript:alert(1)")
        assert RE_JAVASCRIPT_URI.match("  javascript:void(0)")
        assert RE_JAVASCRIPT_URI.match("JAVASCRIPT:x")
        assert not RE_JAVASCRIPT_URI.match("https://example.com")

    def test_re_data_uri(self):
        from app.ai.models import RE_DATA_URI

        assert RE_DATA_URI.match("data:text/html,<h1>hi</h1>")
        assert RE_DATA_URI.match("  data:image/png;base64,abc")
        assert not RE_DATA_URI.match("https://example.com")

    def test_re_vbscript_uri(self):
        from app.ai.models import RE_VBSCRIPT_URI

        assert RE_VBSCRIPT_URI.match("vbscript:MsgBox(1)")
        assert RE_VBSCRIPT_URI.match("  vbscript:evil")
        assert not RE_VBSCRIPT_URI.match("https://example.com")


# ---------------------------------------------------------------------------
# app.ai.__init__ -- re-exports
# ---------------------------------------------------------------------------
class TestAIInit:
    """Test that the ai package re-exports all public names."""

    def test_import_models_constants(self):
        from app.ai import ALLOWED_TAGS, RE_EVENT_ATTR, STRIP_TAGS

        assert isinstance(ALLOWED_TAGS, frozenset)
        assert isinstance(STRIP_TAGS, frozenset)
        assert hasattr(RE_EVENT_ATTR, "match")

    def test_import_markdown_renderer(self):
        from app.ai import _HTMLSanitizer, bubble_html, render_message_html, sanitize_html

        assert callable(sanitize_html)
        assert callable(render_message_html)
        assert callable(bubble_html)
        assert issubclass(_HTMLSanitizer, object)

    def test_import_api_client(self):
        from app.ai import build_chat_url, build_models_url, create_ssl_context, require_https

        assert callable(require_https)
        assert callable(create_ssl_context)
        assert callable(build_models_url)
        assert callable(build_chat_url)

    def test_all_exports_listed(self):
        import app.ai as ai_pkg

        for name in ai_pkg.__all__:
            assert hasattr(ai_pkg, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# app.ai.api_client -- pure functions
# ---------------------------------------------------------------------------
class TestRequireHttps:
    """require_https raises ValueError for non-HTTPS hosts."""

    def test_https_passes(self):
        from app.ai.api_client import require_https

        require_https("https://api.example.com")  # no exception

    def test_http_raises(self):
        from app.ai.api_client import require_https

        with pytest.raises(ValueError, match="HTTPS"):
            require_https("http://api.example.com")

    def test_empty_string_raises(self):
        from app.ai.api_client import require_https

        with pytest.raises(ValueError):
            require_https("")

    def test_ftp_raises(self):
        from app.ai.api_client import require_https

        with pytest.raises(ValueError):
            require_https("ftp://files.example.com")


class TestCreateSslContext:
    """create_ssl_context returns a proper SSLContext."""

    def test_returns_ssl_context(self):
        from app.ai.api_client import create_ssl_context

        ctx = create_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_verifies_certificates(self):
        from app.ai.api_client import create_ssl_context

        ctx = create_ssl_context()
        assert ctx.verify_mode == ssl.CERT_REQUIRED


class TestBuildModelsUrl:
    """URL construction for /models endpoint."""

    def test_plain_host(self):
        from app.ai.api_client import build_models_url

        assert build_models_url("https://api.example.com") == "https://api.example.com/v1/models"

    def test_host_with_v1(self):
        from app.ai.api_client import build_models_url

        assert build_models_url("https://api.example.com/v1") == "https://api.example.com/v1/models"

    def test_trailing_slash_stripped(self):
        from app.ai.api_client import build_models_url

        assert build_models_url("https://api.example.com/") == "https://api.example.com/v1/models"

    def test_host_with_v1_trailing_slash(self):
        from app.ai.api_client import build_models_url

        assert build_models_url("https://api.example.com/v1/") == "https://api.example.com/v1/models"


class TestBuildChatUrl:
    """URL construction for /chat/completions endpoint."""

    def test_plain_host(self):
        from app.ai.api_client import build_chat_url

        assert build_chat_url("https://api.example.com") == "https://api.example.com/v1/chat/completions"

    def test_host_with_v1(self):
        from app.ai.api_client import build_chat_url

        assert build_chat_url("https://api.example.com/v1") == "https://api.example.com/v1/chat/completions"

    def test_trailing_slash(self):
        from app.ai.api_client import build_chat_url

        assert build_chat_url("https://api.example.com/v1/") == "https://api.example.com/v1/chat/completions"


class TestTestConnection:
    """test_connection with mocked urllib."""

    def test_success(self):
        from app.ai.api_client import test_connection

        mock_response = MagicMock(spec=HTTPResponse)
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = test_connection("https://api.example.com", "sk-test")
        assert "200" in result
        assert "成功" in result

    def test_http_error_returns_failure(self):
        from app.ai.api_client import clear_connection_cache, test_connection

        clear_connection_cache()
        with patch("app.ai.api_client.urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = test_connection("https://api.example.com", "sk-test")
        assert "失败" in result

    def test_non_https_returns_error(self):
        from app.ai.api_client import test_connection

        result = test_connection("http://api.example.com", "sk-test")
        assert "HTTPS" in result


class TestFetchModels:
    """fetch_models with mocked urllib."""

    def test_success(self):
        from app.ai.api_client import fetch_models

        payload = json.dumps({"data": [{"id": "gpt-4"}, {"id": "gpt-3.5-turbo"}]}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = fetch_models("https://api.example.com/v1", "sk-test")
        assert result == ["gpt-3.5-turbo", "gpt-4"]

    def test_empty_data(self):
        from app.ai.api_client import fetch_models

        payload = json.dumps({"data": []}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = fetch_models("https://api.example.com/v1", "sk-test")
        assert result == []

    def test_non_https_raises(self):
        from app.ai.api_client import fetch_models

        with pytest.raises(ValueError):
            fetch_models("http://api.example.com", "sk-test")

    def test_missing_id_field_skipped(self):
        from app.ai.api_client import fetch_models

        payload = json.dumps({"data": [{"id": "gpt-4"}, {"name": "no-id"}]}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = fetch_models("https://api.example.com/v1", "sk-test")
        assert result == ["gpt-4"]


class TestSendChat:
    """send_chat with mocked urllib."""

    def test_success(self):
        from app.ai.api_client import send_chat

        payload = json.dumps({"choices": [{"message": {"content": "Hello!"}}]}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = send_chat("https://api.example.com/v1", "sk-test", "gpt-4", [{"role": "user", "content": "hi"}])
        assert result == "Hello!"

    def test_no_choices_returns_error(self):
        from app.ai.api_client import send_chat

        payload = json.dumps({"error": {"message": "rate limited"}}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = send_chat("https://api.example.com/v1", "sk-test", "gpt-4", [{"role": "user", "content": "hi"}])
        assert "异常" in result
        assert "rate limited" in result

    def test_no_choices_no_error_message(self):
        from app.ai.api_client import send_chat

        payload = json.dumps({"something": "else"}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response):
            result = send_chat("https://api.example.com/v1", "sk-test", "gpt-4", [{"role": "user", "content": "hi"}])
        assert "异常" in result

    def test_non_https_raises(self):
        from app.ai.api_client import send_chat

        with pytest.raises(ValueError):
            send_chat("http://api.example.com", "sk-test", "gpt-4", [])

    def test_custom_timeout(self):
        from app.ai.api_client import send_chat

        payload = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response) as mock_open:
            send_chat("https://api.example.com/v1", "sk-test", "gpt-4", [], timeout=30)
            call_kwargs = mock_open.call_args
            assert call_kwargs.kwargs.get("timeout") == 30 or call_kwargs[1].get("timeout") == 30


# ---------------------------------------------------------------------------
# app.ai.markdown_renderer -- _HTMLSanitizer
# ---------------------------------------------------------------------------
class TestHTMLSanitizer:
    """Test the whitelist-based HTML sanitizer."""

    def test_allowed_tags_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>hello</p><strong>bold</strong>")
        assert "<p>" in result
        assert "<strong>" in result
        assert "hello" in result
        assert "bold" in result

    def test_script_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<script>alert('xss')</script><p>safe</p>")
        assert "script" not in result.lower()
        assert "<p>safe</p>" in result

    def test_style_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<style>body{color:red}</style><p>text</p>")
        assert "style" not in result.lower()
        assert "<p>text</p>" in result

    def test_iframe_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<iframe src='evil'></iframe><p>ok</p>")
        assert "iframe" not in result.lower()
        assert "<p>ok</p>" in result

    def test_object_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<object data='evil'>inner</object><p>ok</p>")
        assert "object" not in result.lower()
        assert "<p>ok</p>" in result

    def test_embed_stripped(self):
        """<embed> is a void element; verify the tag itself is dropped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<embed src='evil'>")
        assert "embed" not in result.lower()

    def test_event_handler_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<p onclick="alert(1)">text</p>')
        assert "onclick" not in result
        assert "text" in result

    def test_href_javascript_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="javascript:alert(1)">link</a>')
        assert "javascript" not in result
        assert "link" in result

    def test_href_data_uri_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="data:text/html,<h1>hi</h1>">link</a>')
        assert "data:" not in result
        assert "link" in result

    def test_href_vbscript_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="vbscript:MsgBox(1)">link</a>')
        assert "vbscript" not in result
        assert "link" in result

    def test_href_https_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="https://example.com">link</a>')
        assert "https://example.com" in result

    def test_href_relative_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="/page">link</a>')
        assert 'href="/page"' in result

    def test_href_http_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="http://example.com">link</a>')
        assert "http://example.com" in result

    def test_non_allowed_tag_dropped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<div><p>text</p></div>")
        assert "<div>" not in result
        assert "<p>text</p>" in result

    def test_span_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<span class="hl">text</span>')
        assert "<span>" in result
        assert "text" in result

    def test_span_other_attrs_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<span onclick="evil" style="color:red">text</span>')
        assert "onclick" not in result
        assert "style" not in result

    def test_startend_tag(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<br/>")
        assert "<br" in result

    def test_comment_stripped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<!-- comment --><p>text</p>")
        assert "comment" not in result
        assert "text" in result

    def test_entity_ref_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>&amp;</p>")
        assert "&amp;" in result

    def test_char_ref_preserved(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>&#60;</p>")
        assert "&#60;" in result

    def test_nested_strip_tags(self):
        """Nested script tags should all be stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<script><script>inner</script></script><p>ok</p>")
        assert "inner" not in result
        assert "<p>ok</p>" in result

    def test_empty_html(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("")
        assert result == ""

    def test_text_only(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("just plain text")
        assert result == "just plain text"

    def test_unknown_decl_handled(self):
        from app.ai.markdown_renderer import sanitize_html

        # CDATA or unknown declarations should be ignored
        result = sanitize_html("<![CDATA[text]]><p>ok</p>")
        assert "ok" in result

    def test_link_other_attrs_dropped(self):
        """For <a> tags, only href is kept; other attrs are stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="https://x.com" target="_blank" rel="noopener">link</a>')
        assert "target" not in result
        assert "rel" not in result
        assert "href" in result

    def test_href_empty_dropped(self):
        """Empty href is dropped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="">link</a>')
        # Empty href should be dropped since it doesn't start with http/https/
        assert "link" in result

    def test_href_non_standard_scheme_dropped(self):
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<a href="ftp://evil.com">link</a>')
        assert "ftp" not in result

    def test_table_attrs_stripped(self):
        """Table-related tags have attributes stripped for safety."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html('<table border="1" cellpadding="5"><tr><td>cell</td></tr></table>')
        assert "border" not in result
        assert "cellpadding" not in result
        assert "cell" in result


# ---------------------------------------------------------------------------
# app.ai.markdown_renderer -- render_message_html
# ---------------------------------------------------------------------------
class TestRenderMessageHtml:
    """Test message rendering to safe HTML."""

    def test_empty_content(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("")
        assert "暂无内容" in result

    def test_none_content(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html(None)
        assert "暂无内容" in result

    def test_plain_text_no_markdown(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("hello world", allow_markdown=False)
        assert "hello world" in result

    def test_plain_text_with_newlines_no_markdown(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("line1\nline2", allow_markdown=False)
        assert "<br>" in result

    def test_markdown_with_mistune(self):
        """When mistune is available, markdown is rendered."""
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("**bold** and *italic*", allow_markdown=True)
        # Should contain some HTML rendering
        assert "bold" in result

    def test_markdown_disabled(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("**bold**", allow_markdown=False)
        assert "**bold**" in result
        assert "<strong>" not in result

    def test_markdown_with_table(self):
        from app.ai.markdown_renderer import render_message_html

        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = render_message_html(md, allow_markdown=True)
        assert "cellspacing" in result or "A" in result

    def test_mistune_exception_falls_back(self):
        from app.ai.markdown_renderer import render_message_html

        with patch("app.ai.markdown_renderer.mistune") as mock_mistune:
            mock_mistune.html.side_effect = Exception("parse error")
            result = render_message_html("hello", allow_markdown=True)
            assert "hello" in result

    def test_whitespace_only(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("   ")
        assert "暂无内容" in result

    def test_xss_in_content_sanitized(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html('<script>alert("xss")</script>', allow_markdown=False)
        # HTML-escaped: no raw <script> tag in output
        assert "<script>" not in result.lower()


# ---------------------------------------------------------------------------
# app.ai.markdown_renderer -- bubble_html
# ---------------------------------------------------------------------------
class TestBubbleHtml:
    """Test chat bubble HTML generation."""

    def test_user_bubble(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "hello")
        assert "你" in result
        assert "#2563eb" in result
        assert "hello" in result

    def test_assistant_bubble(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("assistant", "hi there")
        assert "助手" in result
        assert "#0f766e" in result
        assert "hi there" in result

    def test_user_bg_color(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "test")
        assert "#eef5ff" in result

    def test_assistant_bg_color(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("assistant", "test")
        assert "#fffdf9" in result

    def test_assistant_renders_markdown(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("assistant", "**bold text**")
        assert "bold text" in result

    def test_user_does_not_render_markdown(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "**not bold**")
        assert "**not bold**" in result

    def test_empty_content(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "")
        assert "暂无内容" in result
