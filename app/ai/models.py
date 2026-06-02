"""Data classes and constants for the AI mentor module."""

import re

# ---------------------------------------------------------------------------
# HTML sanitization constants
# ---------------------------------------------------------------------------

ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "code",
        "pre",
        "strong",
        "em",
        "b",
        "i",
        "a",
        "blockquote",
        "table",
        "tr",
        "td",
        "th",
        "thead",
        "tbody",
        "hr",
        "span",
    }
)

STRIP_TAGS: frozenset[str] = frozenset({"script", "style", "iframe", "object", "embed"})

# Pattern matches on* event handlers, javascript: href, and data: URI payloads.
RE_EVENT_ATTR: re.Pattern[str] = re.compile(r"^on", re.IGNORECASE)
RE_JAVASCRIPT_URI: re.Pattern[str] = re.compile(r"^\s*javascript\s*:", re.IGNORECASE)
RE_DATA_URI: re.Pattern[str] = re.compile(r"^\s*data\s*:", re.IGNORECASE)
RE_VBSCRIPT_URI: re.Pattern[str] = re.compile(r"^\s*vbscript\s*:", re.IGNORECASE)
