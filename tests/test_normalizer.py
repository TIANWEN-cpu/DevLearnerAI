"""Tests for app.practice.normalizer -- answer normalization logic."""

from app.practice.normalizer import normalize_rows


class TestNormalizeRowsOrdered:
    """Test normalize_rows with ordered=True (preserve original order)."""

    def test_single_column(self):
        rows = [[3], [1], [2]]
        result = normalize_rows(rows, ordered=True)
        assert result == [(3,), (1,), (2,)]

    def test_multi_column(self):
        rows = [["a", 1], ["b", 2]]
        result = normalize_rows(rows, ordered=True)
        assert result == [("a", 1), ("b", 2)]

    def test_empty_rows(self):
        result = normalize_rows([], ordered=True)
        assert result == []

    def test_preserves_order(self):
        rows = [[3, "c"], [1, "a"], [2, "b"]]
        result = normalize_rows(rows, ordered=True)
        assert result[0] == (3, "c")
        assert result[1] == (1, "a")
        assert result[2] == (2, "b")

    def test_converts_lists_to_tuples(self):
        rows = [[1, 2, 3]]
        result = normalize_rows(rows, ordered=True)
        assert isinstance(result[0], tuple)
        assert result[0] == (1, 2, 3)


class TestNormalizeRowsUnordered:
    """Test normalize_rows with ordered=False (sort for comparison)."""

    def test_sorts_single_column(self):
        rows = [[3], [1], [2]]
        result = normalize_rows(rows, ordered=False)
        assert result == [(1,), (2,), (3,)]

    def test_sorts_multi_column(self):
        rows = [["b", 2], ["a", 1]]
        result = normalize_rows(rows, ordered=False)
        assert result == [("a", 1), ("b", 2)]

    def test_empty_rows(self):
        result = normalize_rows([], ordered=False)
        assert result == []

    def test_none_values_sort_as_empty_string(self):
        rows = [[None, "b"], ["a", None]]
        result = normalize_rows(rows, ordered=False)
        # None becomes "" for sorting, so (None, "b") sorts before ("a", None)
        # "" < "a" => (None, "b") first
        assert result[0][0] is None
        assert result[1][0] == "a"

    def test_numeric_sort_as_strings(self):
        """When unordered, values are compared as strings."""
        rows = [[10], [2], [1]]
        result = normalize_rows(rows, ordered=False)
        # String sort: "1" < "10" < "2"
        assert result == [(1,), (10,), (2,)]

    def test_mixed_types(self):
        rows = [["z"], ["a"], ["m"]]
        result = normalize_rows(rows, ordered=False)
        assert result == [("a",), ("m",), ("z",)]

    def test_duplicate_rows_preserved(self):
        rows = [[1], [1], [2]]
        result = normalize_rows(rows, ordered=False)
        assert len(result) == 3
        assert result.count((1,)) == 2

    def test_single_row(self):
        rows = [[42]]
        result = normalize_rows(rows, ordered=False)
        assert result == [(42,)]

    def test_tuple_input(self):
        """Input rows can be tuples already."""
        rows = [(3, "c"), (1, "a")]
        result = normalize_rows(rows, ordered=False)
        assert result == [(1, "a"), (3, "c")]


class TestNormalizeRowsEdgeCases:
    """Edge cases for normalize_rows."""

    def test_empty_inner_rows(self):
        rows = [[], []]
        result = normalize_rows(rows, ordered=True)
        assert result == [(), ()]

    def test_single_element_rows(self):
        rows = [[None]]
        result = normalize_rows(rows, ordered=True)
        assert result == [(None,)]

    def test_large_dataset_ordered(self):
        rows = [[i] for i in range(100)]
        result = normalize_rows(rows, ordered=True)
        assert len(result) == 100
        assert result[0] == (0,)
        assert result[99] == (99,)

    def test_large_dataset_unordered(self):
        rows = [[i] for i in range(100, 0, -1)]
        result = normalize_rows(rows, ordered=False)
        assert len(result) == 100
        # String sort of numbers: "1" < "10" < "100" < "2" ...
        expected = sorted(
            [(i,) for i in range(100, 0, -1)],
            key=lambda row: tuple(str(item) for item in row),
        )
        assert result == expected
