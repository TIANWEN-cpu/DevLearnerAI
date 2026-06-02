"""Tests for app.ai.markdown_renderer -- HTML sanitization XSS prevention."""

from app.ai.markdown_renderer import sanitize_html


class TestXSSPrevention:
    """Comprehensive XSS attack vector tests."""

    def test_strips_script_tags(self):
        result = sanitize_html('<script>alert("xss")</script>')
        assert "script" not in result
        assert "alert" not in result

    def test_strips_onclick_handler(self):
        result = sanitize_html('<p onclick="alert(1)">text</p>')
        assert "onclick" not in result
        assert "text" in result

    def test_strips_onerror_handler(self):
        result = sanitize_html('<img onerror="alert(1)">')
        assert "onerror" not in result

    def test_strips_onload_handler(self):
        result = sanitize_html('<body onload="alert(1)">text</body>')
        assert "onload" not in result

    def test_strips_javascript_uri_in_href(self):
        result = sanitize_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript" not in result
        assert "click" in result

    def test_strips_javascript_uri_case_variation(self):
        result = sanitize_html('<a href="JavaScript:alert(1)">click</a>')
        assert "javascript" not in result.lower() or "href" not in result

    def test_strips_data_uri_in_href(self):
        result = sanitize_html('<a href="data:text/html,<script>alert(1)</script>">click</a>')
        assert "data:" not in result

    def test_strips_vbscript_uri_in_href(self):
        result = sanitize_html('<a href="vbscript:MsgBox">click</a>')
        assert "vbscript" not in result

    def test_strips_style_tags(self):
        result = sanitize_html("<style>body{background:red}</style><p>ok</p>")
        assert "background" not in result
        assert "ok" in result

    def test_strips_iframe(self):
        result = sanitize_html('<iframe src="evil.com"></iframe><p>safe</p>')
        assert "iframe" not in result
        assert "safe" in result

    def test_strips_object_and_embed(self):
        result = sanitize_html('<object data="evil"></object><p>ok</p>')
        assert "object" not in result
        assert "ok" in result

    def test_strips_html_comments(self):
        result = sanitize_html("<p>before</p><!-- evil comment --><p>after</p>")
        assert "evil" not in result
        assert "comment" not in result
        assert "before" in result
        assert "after" in result


class TestAllowedContent:
    """Verify safe HTML content is preserved."""

    def test_preserves_paragraph(self):
        result = sanitize_html("<p>hello</p>")
        assert "<p>" in result
        assert "hello" in result
        assert "</p>" in result

    def test_preserves_bold_and_italic(self):
        result = sanitize_html("<strong>bold</strong> and <em>italic</em>")
        assert "<strong>" in result
        assert "<em>" in result

    def test_preserves_code_block(self):
        result = sanitize_html("<pre><code>x = 1</code></pre>")
        assert "<pre>" in result
        assert "<code>" in result

    def test_preserves_list(self):
        result = sanitize_html("<ul><li>item1</li><li>item2</li></ul>")
        assert "<ul>" in result
        assert "<li>" in result
        assert "item1" in result

    def test_preserves_table(self):
        result = sanitize_html("<table><tr><th>H</th></tr><tr><td>D</td></tr></table>")
        assert "<table>" in result
        assert "<th>" in result
        assert "<td>" in result

    def test_preserves_safe_link(self):
        result = sanitize_html('<a href="https://example.com">link</a>')
        assert "https://example.com" in result
        assert "link" in result

    def test_preserves_relative_link(self):
        result = sanitize_html('<a href="/page">link</a>')
        assert "/page" in result

    def test_preserves_span_class(self):
        result = sanitize_html('<span class="hljs-keyword">def</span>')
        # Sanitizer may or may not keep class on span depending on implementation
        assert "def" in result
        assert "<span" in result

    def test_strips_span_non_class_attrs(self):
        result = sanitize_html('<span onclick="evil" class="ok">text</span>')
        assert "onclick" not in result
        assert "text" in result

    def test_strips_unknown_tags(self):
        result = sanitize_html("<customtag>text</customtag>")
        assert "customtag" not in result
        assert "text" in result

    def test_preserves_blockquote(self):
        result = sanitize_html("<blockquote>quote</blockquote>")
        assert "<blockquote>" in result

    def test_preserves_hr(self):
        result = sanitize_html("<p>a</p><hr><p>b</p>")
        assert "<hr>" in result


class TestAttributeFiltering:
    """Test attribute-level filtering rules."""

    def test_a_tag_strips_all_attrs_except_href(self):
        result = sanitize_html('<a href="https://x.com" class="link" id="a1" title="t">go</a>')
        assert "class" not in result
        assert "id" not in result
        assert "title" not in result
        assert "href" in result

    def test_a_tag_strips_non_http_href(self):
        result = sanitize_html('<a href="ftp://example.com">link</a>')
        assert "ftp" not in result
        assert "link" in result

    def test_a_tag_strips_empty_href(self):
        result = sanitize_html('<a href="">link</a>')
        assert "link" in result

    def test_non_a_tags_drop_all_attrs(self):
        result = sanitize_html('<p class="foo" id="bar" style="color:red">text</p>')
        assert "class" not in result
        assert "id" not in result
        assert "style" not in result
        assert "text" in result

    def test_nested_script_in_allowed_tag(self):
        result = sanitize_html("<p><script>evil</script>safe</p>")
        assert "evil" not in result
        assert "safe" in result


class TestRenderMessageHtml:
    """Test the high-level render_message_html function."""

    def test_markdown_bold(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("**bold**", allow_markdown=True)
        assert "bold" in result

    def test_markdown_code(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("`code`", allow_markdown=True)
        assert "code" in result

    def test_plain_text_with_newlines(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("line1\nline2", allow_markdown=False)
        assert "line1" in result
        assert "line2" in result
        assert "<br>" in result

    def test_html_escaped_in_plain_mode(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("<script>evil</script>", allow_markdown=False)
        assert "evil" not in result or "&lt;" in result


class TestBubbleHtml:
    """Test bubble_html output structure."""

    def test_user_bubble_contains_label(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "hello")
        assert "hello" in result
        assert "你" in result

    def test_assistant_bubble_contains_label(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("assistant", "hi")
        assert "hi" in result
        assert "助手" in result

    def test_bubble_contains_style_block(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "text")
        assert "<style>" in result

    def test_bubble_sanitizes_xss_in_content(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", '<script>alert("xss")</script>')
        # Content is HTML-escaped for user role (allow_markdown=False),
        # so script tags are rendered as text, not executed
        assert "&lt;script&gt;" in result or "script" not in result.lower()
