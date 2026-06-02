"""Extended tests for app.ai.markdown_renderer covering edge cases.

Targets:
- handle_starttag with skip_depth > 0 (line 77)
- handle_endtag with skip_depth > 0 (line 87)
- handle_data with skip_depth > 0 (line 94)
- handle_entityref with skip_depth > 0 (line 105)
- handle_charref with skip_depth > 0 (line 110)
- handle_decl (line 118)
- render_message_html with allow_markdown=False (lines 155-156)
- render_message_html with empty content
"""


class TestHTMLSanitizer:
    """Test the _HTMLSanitizer class edge cases."""

    def test_sanitizer_strips_script_content(self):
        """Script tags and their content should be stripped entirely."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>before</p><script>alert('xss')</script><p>after</p>")
        assert "alert" not in result
        assert "before" in result
        assert "after" in result

    def test_sanitizer_strips_style_content(self):
        """Style tags and their content should be stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>text</p><style>body{color:red}</style><p>end</p>")
        assert "color:red" not in result
        assert "text" in result

    def test_sanitizer_handles_nested_strip_tags(self):
        """Nested strip tags should be handled correctly."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<script><style>bad</style></script><p>ok</p>")
        assert "bad" not in result
        assert "ok" in result

    def test_sanitizer_handles_entity_ref(self):
        """Entity references like &amp; should be kept in allowed context."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>&amp; &lt;</p>")
        assert "&amp;" in result

    def test_sanitizer_handles_entity_ref_inside_strip(self):
        """Entity refs inside stripped tags should be skipped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<script>&amp;</script><p>safe</p>")
        assert "&amp;" not in result

    def test_sanitizer_handles_charref(self):
        """Character references should be preserved."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>&#60;</p>")
        assert "&#60;" in result

    def test_sanitizer_handles_charref_inside_strip(self):
        """Char refs inside stripped tags should be skipped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<script>&#60;</script><p>ok</p>")
        assert "&#60;" not in result

    def test_sanitizer_strips_comments(self):
        """HTML comments should be stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>before</p><!-- comment --><p>after</p>")
        assert "comment" not in result

    def test_sanitizer_strips_declarations(self):
        """DOCTYPE declarations should be stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<!DOCTYPE html><p>text</p>")
        assert "DOCTYPE" not in result

    def test_sanitizer_strips_iframe(self):
        """Iframe tags and content should be stripped."""
        from app.ai.markdown_renderer import sanitize_html

        result = sanitize_html("<p>safe</p><iframe src='evil'></iframe><p>more</p>")
        assert "iframe" not in result.lower() or result.count("iframe") == 0


class TestRenderMessageHtmlEdge:
    """Test render_message_html edge cases."""

    def test_empty_content(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("")
        assert "暂无内容" in result

    def test_none_content(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html(None)
        assert "暂无内容" in result

    def test_whitespace_only_content(self):
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("   \n  ")
        assert "暂无内容" in result

    def test_allow_markdown_false(self):
        """When allow_markdown=False, should return plain escaped text."""
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("Hello <world>", allow_markdown=False)
        assert "Hello" in result

    def test_allow_markdown_true(self):
        """When allow_markdown=True with mistune, should render markdown."""
        from app.ai.markdown_renderer import render_message_html

        result = render_message_html("**bold**", allow_markdown=True)
        assert "bold" in result


class TestBubbleHtml:
    def test_basic_bubble(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("user", "Hello")
        assert "Hello" in result

    def test_assistant_bubble(self):
        from app.ai.markdown_renderer import bubble_html

        result = bubble_html("assistant", "Hi there")
        assert "Hi there" in result
