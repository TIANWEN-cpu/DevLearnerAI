"""Normalization helpers for exercise answer comparison."""


def normalize_rows(rows: list, ordered: bool) -> list[tuple]:
    """Normalize SQL result rows for comparison.

    Converts each row to a tuple and sorts them unless *ordered* is True.
    None values are treated as empty strings for sorting purposes.
    """
    normalized = [tuple(row) for row in rows]
    if ordered:
        return normalized
    return sorted(
        normalized,
        key=lambda row: tuple("" if item is None else str(item) for item in row),
    )
