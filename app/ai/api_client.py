"""AI API 通信模块。

提供与 OpenAI 兼容 API 的通信功能，包括连接测试、模型列表获取和
聊天消息发送。所有通信强制使用 HTTPS，启用 TLS 证书验证。

优化特性：
- 流式响应支持（send_chat_stream）
- 连接状态缓存（避免重复测试）
- 请求去重（防止相同请求并发）
- 结构化日志记录（API 调用时序和 token 统计）
"""

import json
import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from app.utils.metrics import get_metrics

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
                logger.debug("Connection test cache hit for %s", host)
                return status

    logger.info("Testing API connection to %s", host)
    start_time = time.perf_counter()
    try:
        require_https(host)
        ctx = create_ssl_context()
        request = urllib.request.Request(
            build_models_url(host),
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=20, context=ctx) as response:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            result = f"连接成功，状态码 {response.status}。"
            logger.info(
                "Connection test succeeded: host=%s status=%d latency=%.1fms", host, response.status, elapsed_ms
            )
            get_metrics().record_operation("api_connection_test", elapsed_ms, success=True)
    except ValueError as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        result = str(exc)
        logger.warning("Connection test rejected: host=%s reason=%s latency=%.1fms", host, result, elapsed_ms)
        get_metrics().record_operation("api_connection_test", elapsed_ms, success=False)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.warning("连接测试失败 [%s]: %s latency=%.1fms", host, exc, elapsed_ms, exc_info=True)
        result = "连接失败，请检查 Host 地址和网络连接。"
        get_metrics().record_operation("api_connection_test", elapsed_ms, success=False)

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
    logger.info("Fetching models from %s", host)
    start_time = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    models = sorted(item["id"] for item in payload.get("data", []) if "id" in item)
    logger.info("Fetched %d models from %s latency=%.1fms", len(models), host, elapsed_ms)
    get_metrics().record_operation("fetch_models", elapsed_ms, success=True)
    return models


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
            logger.debug("Deduplicated API request served from cache")
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
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            payload = json.loads(response.read().decode("utf-8"))

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        token_count = payload.get("usage", {}).get("total_tokens", 0)

        if not payload.get("choices"):
            error_msg = payload.get("error", {}).get("message", "API 返回了没有 choices 的响应。")
            result = f"AI 响应异常：{error_msg}"
            logger.warning(
                "API response missing choices: model=%s latency=%.1fms error=%s",
                model,
                elapsed_ms,
                error_msg,
            )
            get_metrics().record_api_call(model, success=False, elapsed_ms=elapsed_ms, tokens=token_count)
        else:
            result = payload["choices"][0]["message"]["content"]
            logger.info(
                "API chat completed: model=%s latency=%.1fms tokens=%d reply_len=%d",
                model,
                elapsed_ms,
                token_count,
                len(result),
            )
            get_metrics().record_api_call(model, success=True, elapsed_ms=elapsed_ms, tokens=token_count)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error("API chat failed: model=%s latency=%.1fms error=%s", model, elapsed_ms, exc, exc_info=True)
        get_metrics().record_api_call(model, success=False, elapsed_ms=elapsed_ms)
        raise
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
    start_time = time.perf_counter()
    logger.info("Starting streaming API request: model=%s timeout=%ds", model, timeout)
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
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.warning("流式请求失败（已接收 %d 个片段, 耗时 %.1fms）: %s", len(full_text), elapsed_ms, exc)
        get_metrics().record_api_call(model, success=False, elapsed_ms=elapsed_ms)
        # Fall back to non-streaming ONLY if no chunks were received yet.
        # If partial content was already sent via on_chunk, re-sending would
        # cause duplicate text in the UI.
        if not full_text:
            return send_chat(host, api_key, model, messages, timeout)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    reply = "".join(full_text)
    logger.info(
        "Streaming API request completed: model=%s chunks=%d reply_len=%d latency=%.1fms",
        model,
        len(full_text),
        len(reply),
        elapsed_ms,
    )
    get_metrics().record_api_call(model, success=True, elapsed_ms=elapsed_ms, tokens=len(reply))
    return reply


def clear_connection_cache() -> None:
    """Clear the connection status cache."""
    with _connection_cache_lock:
        _connection_cache.clear()
