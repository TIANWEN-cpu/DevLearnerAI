"""AI API 通信模块。

提供与 OpenAI 兼容 API 的通信功能，包括连接测试、模型列表获取和
聊天消息发送。所有通信强制使用 HTTPS，启用 TLS 证书验证。

优化特性：
- 流式响应支持（send_chat_stream）
- 连接状态缓存（避免重复测试）
- 请求去重（防止相同请求并发）
"""

import json
import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable

logger = logging.getLogger(__name__)

# ── Connection status cache ──────────────────────────────────────────────────

_connection_cache: dict[str, tuple[float, str]] = {}  # (host, key) -> (timestamp, status)
_connection_cache_lock = threading.Lock()
_CONNECTION_CACHE_TTL = 300  # 5 minutes

# ── Request timeout defaults ─────────────────────────────────────────────────

_DEFAULT_REQUEST_TIMEOUT = 60  # seconds for non-streaming requests
_DEFAULT_STREAM_TIMEOUT = 120  # seconds for streaming requests

# ── Request deduplication ────────────────────────────────────────────────────

_pending_requests: dict[str, threading.Event] = {}
_pending_results: dict[str, str] = {}
_request_lock = threading.Lock()


def require_https(host: str) -> None:
    """Raise ValueError if the host does not use HTTPS."""
    if not host.lower().startswith("https://"):
        raise ValueError("出于安全考虑，仅允许 HTTPS 连接。请将 API Host 改为 https:// 开头的地址。")


def create_ssl_context() -> ssl.SSLContext:
    """Return a hardened SSL context that verifies certificates."""
    return ssl.create_default_context()


def build_models_url(host: str) -> str:
    """Build the /models endpoint URL from the given host."""
    base = host.rstrip("/")
    return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"


def build_chat_url(host: str) -> str:
    """Build the /chat/completions endpoint URL from the given host."""
    base = host.rstrip("/")
    return f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"


def test_connection(host: str, api_key: str) -> str:
    """Test API connectivity. Returns a status message string.

    Uses a 5-minute cache to avoid redundant network calls.
    """
    cache_key = f"{host}|{api_key[-8:] if len(api_key) > 8 else api_key}"
    with _connection_cache_lock:
        entry = _connection_cache.get(cache_key)
        if entry is not None:
            ts, status = entry
            if time.monotonic() - ts < _CONNECTION_CACHE_TTL:
                return status

    try:
        require_https(host)
        ctx = create_ssl_context()
        request = urllib.request.Request(
            build_models_url(host),
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=20, context=ctx) as response:
            result = f"连接成功，状态码 {response.status}。"
    except ValueError as exc:
        result = str(exc)
    except Exception as exc:
        logger.warning("连接测试失败 [%s]: %s", host, exc, exc_info=True)
        result = "连接失败，请检查 Host 地址和网络连接。"

    with _connection_cache_lock:
        _connection_cache[cache_key] = (time.monotonic(), result)
    return result


def fetch_models(host: str, api_key: str) -> list[str]:
    """Fetch available model IDs from the API. Raises on failure."""
    require_https(host)
    ctx = create_ssl_context()
    request = urllib.request.Request(
        build_models_url(host),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=30, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return sorted(item["id"] for item in payload.get("data", []) if "id" in item)


def send_chat(
    host: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = _DEFAULT_REQUEST_TIMEOUT,
) -> str:
    """Send a chat completion request. Returns the assistant reply text.

    Includes request deduplication: if an identical request is already in flight,
    waits for its result instead of sending a duplicate.

    Raises ValueError for HTTPS violations, and re-raises HTTP/network errors
    for the caller to handle with user-facing messages.
    """
    require_https(host)

    # Deduplicate identical requests
    request_key = json.dumps({"host": host, "model": model, "messages": messages}, sort_keys=True, ensure_ascii=False)

    with _request_lock:
        if request_key in _pending_requests:
            # Another identical request is in flight; wait for its result
            event = _pending_requests[request_key]
        else:
            _pending_requests[request_key] = threading.Event()
            event = None

    if event is not None:
        event.wait(timeout=timeout)
        result = _pending_results.pop(request_key, None)
        if result is not None:
            return result
        # Fall through to send our own request if the other one timed out

    ctx = create_ssl_context()
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    request = urllib.request.Request(
        build_chat_url(host),
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    result: str = "请求失败"
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not payload.get("choices"):
            error_msg = payload.get("error", {}).get("message", "API 返回了没有 choices 的响应。")
            result = f"AI 响应异常：{error_msg}"
        else:
            result = payload["choices"][0]["message"]["content"]
    finally:
        # Signal any waiters and clean up (always, even on crash)
        with _request_lock:
            _pending_results[request_key] = result
            event_obj = _pending_requests.pop(request_key, None)
            if event_obj:
                event_obj.set()

    return result


def send_chat_stream(
    host: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    on_chunk: Callable[[str], None],
    timeout: int = _DEFAULT_STREAM_TIMEOUT,
) -> str:
    """Send a streaming chat completion request.

    Receives chunks via SSE (Server-Sent Events) and calls on_chunk(text)
    for each delta content. Returns the full assembled reply.

    Args:
        host: API host URL.
        api_key: API key.
        model: Model name.
        messages: Chat messages list.
        on_chunk: Callback invoked with each text chunk.
        timeout: Request timeout in seconds.

    Returns:
        The complete assembled reply text.
    """
    require_https(host)
    ctx = create_ssl_context()
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        build_chat_url(host),
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    full_text = []
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            buffer = ""
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                            delta = obj.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_text.append(content)
                                on_chunk(content)
                        except json.JSONDecodeError:
                            continue
    except Exception as exc:
        logger.warning("流式请求失败（已接收 %d 个片段）: %s", len(full_text), exc)
        # Fall back to non-streaming ONLY if no chunks were received yet.
        # If partial content was already sent via on_chunk, re-sending would
        # cause duplicate text in the UI.
        if not full_text:
            return send_chat(host, api_key, model, messages, timeout)

    return "".join(full_text)


def clear_connection_cache() -> None:
    """Clear the connection status cache."""
    with _connection_cache_lock:
        _connection_cache.clear()
