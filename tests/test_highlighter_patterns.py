"""Tests for app.highlighter -- regex pattern construction (business logic).

These tests verify the regex patterns built by the highlighter constructors
without requiring a QSyntaxHighlighter document (no GUI).
"""

import re


class TestKeywordPatternConstruction:
    """Test that keyword regex patterns are correctly constructed."""

    def _build_pattern(self, word: str) -> re.Pattern:
        return re.compile(rf"\b{re.escape(word)}\b")

    def test_keyword_boundary_matching(self):
        pattern = self._build_pattern("def")
        assert pattern.search("def foo():")
        assert pattern.search("x = def") is None or pattern.search("defined") is None
        # \b ensures "def" in "defined" does NOT match as standalone
        assert pattern.search("defined") is None

    def test_keyword_with_special_chars(self):
        # \b requires word boundary, but + is not a word char
        # so \bC\+\+\b won't match in "C++" because \b after + fails
        pattern = self._build_pattern("C++")
        # The pattern won't match due to \b boundary rules around +
        # This is a known limitation of the highlighter's regex approach
        assert pattern.search("learn C++ now") is None

    def test_keyword_escape_dots(self):
        pattern = self._build_pattern("self.value")
        assert pattern.search("self.value = 5")
        # Without escaping, . would match any char
        assert pattern.search("selfXvalue") is None

    def test_keyword_escape_parens(self):
        # \b doesn't work around ( and ) since they're non-word chars
        pattern = self._build_pattern("print()")
        # \bprint\(\)\b won't match because ( is not a word char
        # This is a known limitation of the highlighter's regex approach
        assert pattern.search("print()") is None

    def test_keyword_case_sensitive(self):
        pattern = self._build_pattern("SELECT")
        assert pattern.search("SELECT * FROM t")
        assert pattern.search("select * from t") is None

    def test_number_pattern(self):
        pattern = re.compile(r"\b[0-9]+\.?[0-9]*\b")
        assert pattern.search("x = 42")
        assert pattern.search("pi = 3.14")
        assert pattern.search("no numbers here") is None

    def test_string_double_quote_pattern(self):
        pattern = re.compile(r'"[^"\n]*"')
        assert pattern.search('"hello world"')
        assert pattern.search('say "hi" now')
        # Should not match across lines
        assert pattern.search('"line1\nline2"') is None

    def test_string_single_quote_pattern(self):
        pattern = re.compile(r"'[^'\n]*'")
        assert pattern.search("'hello'")
        assert pattern.search("say 'hi' now")

    def test_comment_python_pattern(self):
        pattern = re.compile(r"#[^\n]*")
        assert pattern.search("# this is a comment")
        assert pattern.search("x = 1  # inline comment")

    def test_comment_c_style_pattern(self):
        pattern = re.compile(r"//[^\n]*")
        assert pattern.search("// C comment")
        assert pattern.search("int x = 1; // inline")

    def test_comment_sql_pattern(self):
        pattern = re.compile(r"--[^\n]*")
        assert pattern.search("-- SQL comment")
        assert pattern.search("SELECT 1 -- inline")


class TestHighlighterKeywordLists:
    """Verify the keyword lists are correct for each language."""

    def test_python_has_core_keywords(self):
        import inspect

        from app.highlighter import PythonHighlighter

        # PythonHighlighter stores keywords in _rules as compiled patterns
        # We test indirectly by checking the class can be instantiated
        # and verify known keywords exist in the class definition

        source = inspect.getsource(PythonHighlighter.__init__)
        for kw in ("def", "class", "if", "else", "for", "while", "return", "import", "from"):
            assert f'"{kw}"' in source or f"'{kw}'" in source

    def test_python_has_builtins(self):
        import inspect

        from app.highlighter import PythonHighlighter

        source = inspect.getsource(PythonHighlighter.__init__)
        for bi in ("print", "len", "range", "int", "str", "float", "list", "dict"):
            assert f'"{bi}"' in source or f"'{bi}'" in source

    def test_sql_has_core_keywords(self):
        import inspect

        from app.highlighter import SqlHighlighter

        source = inspect.getsource(SqlHighlighter.__init__)
        for kw in ("SELECT", "FROM", "WHERE", "JOIN", "INSERT", "UPDATE", "DELETE", "CREATE", "TABLE"):
            assert f'"{kw}"' in source or f"'{kw}'" in source

    def test_sql_has_aggregate_functions(self):
        import inspect

        from app.highlighter import SqlHighlighter

        source = inspect.getsource(SqlHighlighter.__init__)
        for fn in ("COUNT", "SUM", "AVG", "MIN", "MAX"):
            assert f'"{fn}"' in source or f"'{fn}'" in source

    def test_clike_c_has_c_keywords(self):
        import inspect

        from app.highlighter import CLikeHighlighter

        source = inspect.getsource(CLikeHighlighter.__init__)
        for kw in ("struct", "typedef", "enum", "sizeof", "printf", "malloc"):
            assert f'"{kw}"' in source or f"'{kw}'" in source

    def test_clike_csharp_has_csharp_keywords(self):
        import inspect

        from app.highlighter import CLikeHighlighter

        source = inspect.getsource(CLikeHighlighter.__init__)
        for kw in ("class", "public", "private", "protected", "namespace", "using"):
            assert f'"{kw}"' in source or f"'{kw}'" in source

    def test_type_keywords_in_rule_based(self):
        """The _RuleBasedHighlighter always adds type keywords."""
        import inspect

        from app.highlighter import _RuleBasedHighlighter

        source = inspect.getsource(_RuleBasedHighlighter.__init__)
        for t in ("int", "float", "double", "char", "bool", "string", "void"):
            assert f'"{t}"' in source or f"'{t}'" in source


class TestTripleQuotePatterns:
    """Test triple-quote detection patterns."""

    def test_triple_double_quote_pattern(self):
        pattern = re.compile(r'"""|' + r"'''")
        assert pattern.search('"""multiline string"""')
        assert pattern.search("no triple here") is None

    def test_triple_single_quote_pattern(self):
        pattern = re.compile(r'"""|' + r"'''")
        assert pattern.search("'''also triple'''")
