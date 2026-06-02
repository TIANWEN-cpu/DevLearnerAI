"""Extended tests for app.ai.api_client to cover missing code paths.

Targets:
- test_connection exception handling (ConnectionError, TimeoutError, generic)
- send_chat dedup path (wait for in-flight request)
- send_chat_stream SSE parsing and fallback
- clear_connection_cache
"""

import json
import threading
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# app.ai.api_client - test_connection edge cases
# ---------------------------------------------------------------------------
class TestTestConnectionErrors:
    """Cover exception branches in test_connection (lines 82-83)."""

    def test_connection_generic_exception_returns_failure(self):
        from app.ai.api_client import _connection_cache, _connection_cache_lock, test_connection

        with _connection_cache_lock:
            _connection_cache.clear()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_models_url", return_value="https://x/v1/models"),
            patch("app.ai.api_client.urllib.request.urlopen", side_effect=RuntimeError("boom")),
        ):
            result = test_connection("https://host", "key")
        assert "连接失败" in result or "失败" in result

    def test_connection_value_error_returns_message(self):
        from app.ai.api_client import _connection_cache, _connection_cache_lock, test_connection

        with _connection_cache_lock:
            _connection_cache.clear()

        with patch("app.ai.api_client.require_https", side_effect=ValueError("bad url")):
            result = test_connection("ftp://host", "key")
        assert "bad url" in result


# ---------------------------------------------------------------------------
# app.ai.api_client - send_chat dedup
# ---------------------------------------------------------------------------
class TestSendChatDedup:
    """Cover the request deduplication logic in send_chat (lines 124-136)."""

    def test_send_chat_dedup_waits_for_inflight(self):
        """When an identical request is in flight, the second call should wait."""
        from app.ai import api_client

        # Clear global state
        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

        messages = [{"role": "user", "content": "hi"}]
        host = "https://api.example.com"
        model = "gpt-4"
        api_key = "test-key"

        # Simulate an in-flight request by pre-populating the pending requests
        request_key = json.dumps(
            {"host": host, "model": model, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
        )
        event = threading.Event()
        with api_client._request_lock:
            api_client._pending_requests[request_key] = event

        # Start the dedup consumer in a thread

        def _wait():
            with (
                patch("app.ai.api_client.require_https"),
                patch("app.ai.api_client.create_ssl_context", return_value=None),
            ):
                # The dedup code checks event.wait(), so let's simulate:
                # The consumer will find an in-flight request and wait on the event.
                # We need to manually set the result and event.
                pass

        # Manually simulate the dedup path: set result, signal event
        with api_client._request_lock:
            api_client._pending_results[request_key] = "deduped response"
            event.set()

        with patch("app.ai.api_client.require_https"), patch("app.ai.api_client.create_ssl_context", return_value=None):
            result = api_client.send_chat(host, api_key, model, messages, timeout=5)

        assert result == "deduped response"

        # Cleanup
        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

    def test_send_chat_dedup_timeout_falls_through(self):
        """When dedup wait times out, should fall through to send own request."""
        from app.ai import api_client

        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

        messages = [{"role": "user", "content": "hi"}]
        host = "https://api.example.com"
        model = "gpt-4"
        api_key = "test-key"

        request_key = json.dumps(
            {"host": host, "model": model, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
        )
        event = threading.Event()
        with api_client._request_lock:
            api_client._pending_requests[request_key] = event

        # Don't set result, so the wait times out and result is None -> falls through
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"choices": [{"message": {"content": "fallback"}}]}).encode(
            "utf-8"
        )
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat(host, api_key, model, messages, timeout=1)

        assert result == "fallback"

        # Cleanup
        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()


# ---------------------------------------------------------------------------
# app.ai.api_client - send_chat error paths
# ---------------------------------------------------------------------------
class TestSendChatErrors:
    """Cover send_chat error / no-choices paths."""

    def test_send_chat_no_choices_returns_error_msg(self):
        from app.ai import api_client

        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"error": {"message": "rate limited"}}).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat("https://h", "key", "model", [{"role": "user", "content": "hi"}])

        assert "AI 响应异常" in result

    def test_send_chat_no_choices_no_error_key(self):
        from app.ai import api_client

        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({}).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat("https://h", "key", "model", [{"role": "user", "content": "hi"}])

        assert "choices" in result or "响应异常" in result


# ---------------------------------------------------------------------------
# app.ai.api_client - send_chat_stream
# ---------------------------------------------------------------------------
class TestSendChatStream:
    """Cover send_chat_stream SSE parsing (lines 209-241)."""

    def test_stream_normal_sse_parsing(self):
        from app.ai import api_client

        sse_data = (
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n'
            'data: {"choices":[{"delta":{"content":" World"}}]}\n'
            "data: [DONE]\n"
        )
        mock_response = MagicMock()
        # Simulate reading chunks
        encoded = sse_data.encode("utf-8")
        chunks = [encoded[i : i + 1024] for i in range(0, len(encoded), 1024)]
        mock_response.read = MagicMock(side_effect=chunks + [b""])
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        on_chunk = MagicMock()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat_stream(
                "https://h",
                "key",
                "model",
                [{"role": "user", "content": "hi"}],
                on_chunk,
            )

        assert "Hello" in result
        assert "World" in result
        assert on_chunk.call_count >= 2

    def test_stream_fallback_to_non_streaming(self):
        """When streaming fails with no text received, fall back to send_chat."""
        from app.ai import api_client

        with api_client._request_lock:
            api_client._pending_requests.clear()
            api_client._pending_results.clear()

        on_chunk = MagicMock()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", side_effect=RuntimeError("net")),
            patch("app.ai.api_client.send_chat", return_value="fallback reply"),
        ):
            result = api_client.send_chat_stream(
                "https://h",
                "key",
                "model",
                [{"role": "user", "content": "hi"}],
                on_chunk,
            )

        assert result == "fallback reply"

    def test_stream_json_error_in_sse_line(self):
        """SSE lines with invalid JSON should be skipped."""
        from app.ai import api_client

        sse_data = 'data: {invalid json}\ndata: {"choices":[{"delta":{"content":"OK"}}]}\ndata: [DONE]\n'
        encoded = sse_data.encode("utf-8")
        chunks = [encoded[i : i + 1024] for i in range(0, len(encoded), 1024)]

        mock_response = MagicMock()
        mock_response.read = MagicMock(side_effect=chunks + [b""])
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        on_chunk = MagicMock()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat_stream(
                "https://h",
                "key",
                "model",
                [{"role": "user", "content": "hi"}],
                on_chunk,
            )

        assert "OK" in result

    def test_stream_comment_lines_skipped(self):
        """Lines starting with : should be skipped."""
        from app.ai import api_client

        sse_data = ': this is a comment\ndata: {"choices":[{"delta":{"content":"Yes"}}]}\ndata: [DONE]\n'
        encoded = sse_data.encode("utf-8")
        chunks = [encoded[i : i + 1024] for i in range(0, len(encoded), 1024)]

        mock_response = MagicMock()
        mock_response.read = MagicMock(side_effect=chunks + [b""])
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        on_chunk = MagicMock()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat_stream(
                "https://h",
                "key",
                "model",
                [{"role": "user", "content": "hi"}],
                on_chunk,
            )

        assert "Yes" in result

    def test_stream_empty_delta_content_skipped(self):
        """Delta with empty content should not call on_chunk."""
        from app.ai import api_client

        sse_data = 'data: {"choices":[{"delta":{}}]}\ndata: {"choices":[{"delta":{"content":"Final"}}]}\ndata: [DONE]\n'
        encoded = sse_data.encode("utf-8")
        chunks = [encoded[i : i + 1024] for i in range(0, len(encoded), 1024)]

        mock_response = MagicMock()
        mock_response.read = MagicMock(side_effect=chunks + [b""])
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        on_chunk = MagicMock()

        with (
            patch("app.ai.api_client.require_https"),
            patch("app.ai.api_client.create_ssl_context", return_value=None),
            patch("app.ai.api_client.build_chat_url", return_value="https://x"),
            patch("app.ai.api_client.urllib.request.urlopen", return_value=mock_response),
        ):
            result = api_client.send_chat_stream(
                "https://h",
                "key",
                "model",
                [{"role": "user", "content": "hi"}],
                on_chunk,
            )

        assert "Final" in result
        on_chunk.assert_called_once_with("Final")


# ---------------------------------------------------------------------------
# clear_connection_cache
# ---------------------------------------------------------------------------
class TestClearConnectionCache:
    def test_clear_connection_cache(self):
        from app.ai.api_client import _connection_cache, _connection_cache_lock, clear_connection_cache

        with _connection_cache_lock:
            _connection_cache["test"] = (0.0, "cached")
        clear_connection_cache()
        with _connection_cache_lock:
            assert len(_connection_cache) == 0
