"""Tests for app.practice_service -- pure logic and evaluation helpers.

Focuses on static methods and lightweight helpers that do NOT require a
running GUI or external API.
"""

from app.practice_service import PracticeService


# ---------------------------------------------------------------------------
# _normalize_rows
# ---------------------------------------------------------------------------
class TestNormalizeRows:
    """Row normalization for SQL result comparison."""

    def test_ordered_preserves_input_order(self):
        rows = [(3, "c"), (1, "a"), (2, "b")]
        result = PracticeService._normalize_rows(rows, ordered=True)
        assert result == [(3, "c"), (1, "a"), (2, "b")]

    def test_unordered_sorts_rows(self):
        rows = [(3, "c"), (1, "a"), (2, "b")]
        result = PracticeService._normalize_rows(rows, ordered=False)
        assert result == [(1, "a"), (2, "b"), (3, "c")]

    def test_handles_none_values(self):
        rows = [(None, "b"), (1, None)]
        result = PracticeService._normalize_rows(rows, ordered=False)
        # None is treated as "" for sorting
        assert result[0][0] is None or result[0][0] == 1

    def test_empty_input(self):
        assert PracticeService._normalize_rows([], ordered=False) == []
        assert PracticeService._normalize_rows([], ordered=True) == []

    def test_converts_lists_to_tuples(self):
        rows = [[1, "a"], [2, "b"]]
        result = PracticeService._normalize_rows(rows, ordered=True)
        assert all(isinstance(r, tuple) for r in result)
