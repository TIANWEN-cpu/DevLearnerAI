import re

from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter


class _RuleBasedHighlighter(QSyntaxHighlighter):
    def __init__(self, keywords=None, builtins=None, comment_patterns=None, parent=None):
        super().__init__(parent)
        self._rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#2563eb"))
        keyword_format.setFontWeight(QFont.Bold)
        for word in keywords or []:
            self._rules.append((re.compile(rf"\b{re.escape(word)}\b"), keyword_format))

        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#a16207"))
        for word in builtins or []:
            self._rules.append((re.compile(rf"\b{re.escape(word)}\b"), builtin_format))

        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#7c3aed"))
        for word in ["int", "float", "double", "char", "bool", "string", "var", "void", "List", "Dictionary"]:
            self._rules.append((re.compile(rf"\b{re.escape(word)}\b"), type_format))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#0f9d58"))
        self._rules.append((re.compile(r"\b[0-9]+\.?[0-9]*\b"), number_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#b45309"))
        self._rules.append((re.compile(r'"[^"\n]*"'), string_format))
        self._rules.append((re.compile(r"'[^'\n]*'"), string_format))

        self._triple_quote_start = re.compile(r'"""|' + r"'''")
        self._triple_quote_end = re.compile(r'"""|' + r"'''")
        self._string_format = string_format

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6b7280"))
        comment_format.setFontItalic(True)
        for pattern in comment_patterns or []:
            self._rules.append((re.compile(pattern), comment_format))

    def highlightBlock(self, text):
        # Handle multiline (triple-quoted) strings.
        # State 0 = normal, State 1 = inside a triple-quoted string.
        state = self.previousBlockState()
        start_index = 0

        if state == 1:
            # Continue from previous block: search for closing triple-quote.
            end_match = self._triple_quote_end.search(text, start_index)
            if end_match:
                # Found the end of the multiline string on this line.
                length = end_match.end() - start_index
                self.setFormat(start_index, length, self._string_format)
                start_index = end_match.end()
                self.setCurrentBlockState(0)
            else:
                # Entire line is still inside the multiline string.
                self.setFormat(0, len(text), self._string_format)
                self.setCurrentBlockState(1)
                return

        # Apply normal single-line rules first.
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Now scan for new triple-quote starts (that are not inside single-line strings).
        self.setCurrentBlockState(0)
        search_pos = start_index
        while search_pos < len(text):
            start_match = self._triple_quote_start.search(text, search_pos)
            if not start_match:
                break
            # Skip if this position was already formatted as a single-line string.
            fmt_at = self.format(start_match.start())
            if fmt_at and fmt_at.foreground().color() == QColor("#b45309"):
                search_pos = start_match.end()
                continue
            # Search for the closing triple-quote on the same line.
            end_match = self._triple_quote_end.search(text, start_match.end())
            if end_match:
                length = end_match.end() - start_match.start()
                self.setFormat(start_match.start(), length, self._string_format)
                search_pos = end_match.end()
            else:
                # No closing triple-quote on this line -- goes to next block.
                self.setFormat(start_match.start(), len(text) - start_match.start(), self._string_format)
                self.setCurrentBlockState(1)
                break


class PythonHighlighter(_RuleBasedHighlighter):
    def __init__(self, parent=None):
        super().__init__(
            keywords=[
                "and", "as", "assert", "break", "class", "continue", "def",
                "del", "elif", "else", "except", "False", "finally", "for",
                "from", "global", "if", "import", "in", "is", "lambda", "None",
                "nonlocal", "not", "or", "pass", "raise", "return", "True",
                "try", "while", "with", "yield", "async", "await",
            ],
            builtins=[
                "print", "len", "range", "int", "str", "float", "list", "dict",
                "set", "tuple", "type", "isinstance", "enumerate", "zip", "map",
                "filter", "sorted", "reversed", "super", "open", "input",
            ],
            comment_patterns=[r"#[^\n]*"],
            parent=parent,
        )


class CLikeHighlighter(_RuleBasedHighlighter):
    def __init__(self, language: str, parent=None):
        if language == "c":
            keywords = [
                "if", "else", "for", "while", "do", "switch", "case", "break",
                "continue", "return", "struct", "typedef", "enum", "sizeof",
                "static", "const", "volatile", "goto",
            ]
            builtins = ["printf", "scanf", "malloc", "free", "fopen", "fclose", "fgets", "puts"]
        else:
            keywords = [
                "if", "else", "for", "foreach", "while", "switch", "case", "break",
                "continue", "return", "class", "public", "private", "protected",
                "static", "new", "namespace", "using", "try", "catch", "finally",
                "async", "await",
            ]
            builtins = ["Console", "WriteLine", "TryParse", "Task", "List", "Dictionary"]
        super().__init__(
            keywords=keywords,
            builtins=builtins,
            comment_patterns=[r"//[^\n]*"],
            parent=parent,
        )


class SqlHighlighter(_RuleBasedHighlighter):
    def __init__(self, parent=None):
        super().__init__(
            keywords=[
                "SELECT", "FROM", "WHERE", "GROUP", "BY", "ORDER", "HAVING",
                "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "INSERT",
                "INTO", "VALUES", "UPDATE", "DELETE", "CREATE", "TABLE",
                "AS", "DISTINCT", "LIMIT", "OFFSET", "UNION", "EXISTS",
            ],
            builtins=["COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE"],
            comment_patterns=[r"--[^\n]*"],
            parent=parent,
        )
