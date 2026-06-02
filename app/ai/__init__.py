"""AI mentor package -- re-exports public names for convenience.

Submodules:
- ai.models:       HTML sanitization constants and regex patterns
- ai.markdown_renderer: Markdown rendering, HTML sanitization, chat bubbles
- ai.api_client:   API communication helpers (HTTPS, SSL, URL construction)
- ai.chat_handler: AIMentorPanel and AIMentorDock UI classes
"""

from app.ai.api_client import (
    build_chat_url,
    build_models_url,
    create_ssl_context,
    fetch_models,
    require_https,
    send_chat,
    send_chat_stream,
    test_connection,
)
from app.ai.chat_handler import AIMentorDock, AIMentorPanel
from app.ai.markdown_renderer import (
    _HTMLSanitizer,
    bubble_html,
    render_message_html,
    sanitize_html,
)
from app.ai.models import (
    ALLOWED_TAGS,
    RE_DATA_URI,
    RE_EVENT_ATTR,
    RE_JAVASCRIPT_URI,
    RE_VBSCRIPT_URI,
    STRIP_TAGS,
)

__all__ = [
    # models
    "ALLOWED_TAGS",
    "STRIP_TAGS",
    "RE_EVENT_ATTR",
    "RE_JAVASCRIPT_URI",
    "RE_DATA_URI",
    "RE_VBSCRIPT_URI",
    # markdown_renderer
    "_HTMLSanitizer",
    "sanitize_html",
    "render_message_html",
    "bubble_html",
    # api_client
    "require_https",
    "create_ssl_context",
    "build_models_url",
    "build_chat_url",
    "test_connection",
    "fetch_models",
    "send_chat",
    "send_chat_stream",
    # chat_handler
    "AIMentorPanel",
    "AIMentorDock",
]
