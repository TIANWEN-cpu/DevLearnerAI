"""Markdown rendering and HTML sanitization for AI chat bubbles."""

from html import escape
from html.parser import HTMLParser

from app.ai.models import (
    ALLOWED_TAGS,
    RE_DATA_URI,
    RE_EVENT_ATTR,
    RE_JAVASCRIPT_URI,
    RE_VBSCRIPT_URI,
    STRIP_TAGS,
)

try:
    import mistune
except Exception:  # pragma: no cover
    mistune = None


class _HTMLSanitizer(HTMLParser):
    """Whitelist-based HTML sanitizer using the standard-library html.parser."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._result: list[str] = []
        self._skip_depth: int = 0

    # -- helpers ----------------------------------------------------------

    def _safe_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        """Return a string of sanitized attributes for *tag*."""
        safe_parts: list[str] = []
        for name, value in attrs:
            name_lower = name.lower()
            # Strip all on* event handler attributes (onclick, onerror, onload, etc.)
            if RE_EVENT_ATTR.match(name_lower):
                continue
            # For <a> tags, only keep href and only if it is a safe scheme.
            if tag == "a":
                if name_lower == "href":
                    val = (value or "").strip()
                    if RE_JAVASCRIPT_URI.match(val):
                        continue
                    if RE_DATA_URI.match(val):
                        continue
                    if RE_VBSCRIPT_URI.match(val):
                        continue
                    # Only allow http/https/relative (relative paths are harmless in QTextBrowser)
                    if val and not val.startswith(("http://", "https://", "/")):
                        continue
                    safe_parts.append(f' href="{escape(val, quote=True)}"')
                # Drop all other attributes on <a> tags.
                continue
            # For <span>, allow class (for code-highlighting) but nothing else dangerous.
            if tag == "span" and name_lower not in ("class",):
                continue
            # For table-related tags and others, drop all attributes to be safe.
        return "".join(safe_parts)

    # -- parser callbacks -------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in STRIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag_lower in ALLOWED_TAGS:
            self._result.append(f"<{tag_lower}{self._safe_attrs(tag_lower, attrs)}>")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in STRIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth > 0:
            return
        if tag_lower in ALLOWED_TAGS:
            self._result.append(f"</{tag_lower}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in STRIP_TAGS or self._skip_depth > 0:
            return
        if tag_lower in ALLOWED_TAGS:
            self._result.append(f"<{tag_lower}{self._safe_attrs(tag_lower, attrs)} />")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self._result.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth > 0:
            return
        self._result.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._skip_depth > 0:
            return
        self._result.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        # Strip all HTML comments (can contain conditional IE exploits, etc.)
        pass

    def handle_decl(self, decl: str) -> None:
        pass

    def unknown_decl(self, data: str) -> None:
        pass

    # -- public API -------------------------------------------------------

    def sanitize(self, html: str) -> str:
        self._result = []
        self._skip_depth = 0
        self.feed(html)
        self.close()
        return "".join(self._result)


def sanitize_html(html: str) -> str:
    """Strip dangerous HTML while keeping a safe whitelist of tags/attributes."""
    sanitizer = _HTMLSanitizer()
    return sanitizer.sanitize(html)


def render_message_html(content: str, allow_markdown: bool = True) -> str:
    """Render a message string to safe HTML, optionally via mistune Markdown."""
    text = (content or "").strip()
    if not text:
        return "<span style='color:#94a3b8;'>暂无内容。</span>"
    if allow_markdown and mistune is not None:
        try:
            rendered = mistune.html(text)
            rendered = rendered.replace("<table>", "<table cellspacing='0' cellpadding='6'>")
            return sanitize_html(rendered)
        except Exception:
            pass
    return escape(text).replace("\n", "<br>")


def bubble_html(role: str, content: str) -> str:
    """Build an HTML bubble block for a single chat message."""
    role_label = "你" if role == "user" else "助手"
    role_color = "#2563eb" if role == "user" else "#0f766e"
    bubble_bg = "#eef5ff" if role == "user" else "#fffdf9"
    bubble_border = "#cfe0ff" if role == "user" else "#e7e5df"
    body = render_message_html(content, allow_markdown=(role == "assistant"))
    return f"""
    <div style="margin: 0 0 16px 0;">
      <div style="margin-bottom: 6px; color: {role_color}; font-weight: 700; font-size: 14px;">{role_label}</div>
      <div style="
        background: {bubble_bg};
        border: 1px solid {bubble_border};
        border-radius: 18px;
        padding: 14px 16px;
        color: #0f172a;
        line-height: 1.72;
        font-size: 15px;
      ">{body}</div>
    </div>
    """
