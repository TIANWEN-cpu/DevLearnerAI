"""API communication helpers for the AI mentor: HTTPS, SSL, URL construction."""

import json
import logging
import ssl
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


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
    """Test API connectivity. Returns a status message string."""
    try:
        require_https(host)
        ctx = create_ssl_context()
        request = urllib.request.Request(
            build_models_url(host),
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=20, context=ctx) as response:
            return f"连接成功，状态码 {response.status}。"
    except ValueError as exc:
        return str(exc)
    except Exception:
        return "连接失败，请检查 Host 地址和网络连接。"


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
    timeout: int = 90,
) -> str:
    """Send a chat completion request. Returns the assistant reply text.

    Raises ValueError for HTTPS violations, and re-raises HTTP/network errors
    for the caller to handle with user-facing messages.
    """
    require_https(host)
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
    with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload.get("choices"):
        error_msg = payload.get("error", {}).get("message", "API 返回了没有 choices 的响应。")
        return f"AI 响应异常：{error_msg}"
    return payload["choices"][0]["message"]["content"]
