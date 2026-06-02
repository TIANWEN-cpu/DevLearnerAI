"""练习答案比较的标准化工具模块。

提供 SQL 结果集的标准化功能，支持有序和无序比较。
"""

from typing import Any


def normalize_rows(rows: list[Any], ordered: bool) -> list[tuple[Any, ...]]:
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
