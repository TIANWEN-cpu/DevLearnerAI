"""Tests for app.ai.models -- HTML sanitization constants and regex patterns."""


class TestAllowedTags:
    """Verify the ALLOWED_TAGS whitelist is correct."""

    def test_contains_common_safe_tags(self):
        from app.ai.models import ALLOWED_TAGS

        for tag in ("p", "br", "strong", "em", "a", "code", "pre", "ul", "ol", "li"):
            assert tag in ALLOWED_TAGS

    def test_contains_table_tags(self):
        from app.ai.models import ALLOWED_TAGS

        for tag in ("table", "tr", "td", "th", "thead", "tbody"):
            assert tag in ALLOWED_TAGS

    def test_contains_heading_tags(self):
        from app.ai.models import ALLOWED_TAGS

        for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            assert tag in ALLOWED_TAGS

    def test_is_frozen_set(self):
        from app.ai.models import ALLOWED_TAGS

        assert isinstance(ALLOWED_TAGS, frozenset)


class TestStripTags:
    """Verify STRIP_TAGS contains dangerous tags."""

    def test_contains_script(self):
        from app.ai.models import STRIP_TAGS

        assert "script" in STRIP_TAGS

    def test_contains_style(self):
        from app.ai.models import STRIP_TAGS

        assert "style" in STRIP_TAGS

    def test_contains_iframe(self):
        from app.ai.models import STRIP_TAGS

        assert "iframe" in STRIP_TAGS

    def test_contains_embed_and_object(self):
        from app.ai.models import STRIP_TAGS

        assert "embed" in STRIP_TAGS
        assert "object" in STRIP_TAGS

    def test_no_overlap_with_allowed(self):
        from app.ai.models import ALLOWED_TAGS, STRIP_TAGS

        assert ALLOWED_TAGS.isdisjoint(STRIP_TAGS)


class TestRegexPatterns:
    """Test the compiled regex patterns for security filtering."""

    def test_event_attr_matches_onclick(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("onclick")

    def test_event_attr_matches_onerror(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("onerror")

    def test_event_attr_matches_onload(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("onload")

    def test_event_attr_matches_onmouseover(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("onmouseover")

    def test_event_attr_case_insensitive(self):
        from app.ai.models import RE_EVENT_ATTR

        assert RE_EVENT_ATTR.match("ONCLICK")
        assert RE_EVENT_ATTR.match("OnClick")

    def test_event_attr_no_match_on_normal(self):
        from app.ai.models import RE_EVENT_ATTR

        assert not RE_EVENT_ATTR.match("href")
        assert not RE_EVENT_ATTR.match("class")
        assert not RE_EVENT_ATTR.match("src")

    def test_javascript_uri_basic(self):
        from app.ai.models import RE_JAVASCRIPT_URI

        assert RE_JAVASCRIPT_URI.match("javascript:alert(1)")

    def test_javascript_uri_with_spaces(self):
        from app.ai.models import RE_JAVASCRIPT_URI

        assert RE_JAVASCRIPT_URI.match("  javascript:alert(1)")

    def test_javascript_uri_case_insensitive(self):
        from app.ai.models import RE_JAVASCRIPT_URI

        assert RE_JAVASCRIPT_URI.match("JavaScript:void(0)")
        assert RE_JAVASCRIPT_URI.match("JAVASCRIPT:alert")

    def test_javascript_uri_no_match_on_http(self):
        from app.ai.models import RE_JAVASCRIPT_URI

        assert not RE_JAVASCRIPT_URI.match("https://example.com")
        assert not RE_JAVASCRIPT_URI.match("http://example.com")

    def test_data_uri_basic(self):
        from app.ai.models import RE_DATA_URI

        assert RE_DATA_URI.match("data:text/html,<h1>hi</h1>")

    def test_data_uri_with_spaces(self):
        from app.ai.models import RE_DATA_URI

        assert RE_DATA_URI.match("  data:text/html;base64,PHNjcmlwdD4=")

    def test_data_uri_no_match_on_normal(self):
        from app.ai.models import RE_DATA_URI

        assert not RE_DATA_URI.match("https://example.com")

    def test_vbscript_uri_basic(self):
        from app.ai.models import RE_VBSCRIPT_URI

        assert RE_VBSCRIPT_URI.match("vbscript:MsgBox")

    def test_vbscript_uri_case_insensitive(self):
        from app.ai.models import RE_VBSCRIPT_URI

        assert RE_VBSCRIPT_URI.match("VBSCRIPT:evil")

    def test_vbscript_uri_no_match_on_normal(self):
        from app.ai.models import RE_VBSCRIPT_URI

        assert not RE_VBSCRIPT_URI.match("https://example.com")
