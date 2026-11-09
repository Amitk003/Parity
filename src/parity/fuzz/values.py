"""Edge case value library.

Each category returns tricky values for one kind of
column. Values are plain Python values. They load into
both databases unchanged, so any result difference
comes from the databases, not from the data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

CATEGORIES: tuple[str, ...] = (
    "null",
    "empty_string",
    "single_space",
    "trailing_space",
    "mixed_case",
    "unicode",
    "long_string",
    "extreme_int",
    "rounding_number",
    "dst_date",
    "timezone_date",
)


def values_for_category(category: str) -> tuple[Any, ...]:
    """Return edge case values for one category."""
    builders: dict[str, tuple[Any, ...]] = {
        "null": (None,),
        "empty_string": ("",),
        "single_space": (" ",),
        "trailing_space": ("alice ", "bob  "),
        "mixed_case": ("Alice", "ALICE", "aLiCe"),
        "unicode": ("caf\u00e9", "na\u00efve", "\u65e5\u672c", "emoji \U0001f600"),
        "long_string": ("x" * 40,),
        "extreme_int": (0, -1, 2147483647, -2147483648),
        "rounding_number": (Decimal("2.5"), Decimal("3.5"), Decimal("0.125"), Decimal("-2.5")),
        "dst_date": (
            date(2024, 3, 10),
            date(2024, 11, 3),
            date(2024, 2, 29),
        ),
        "timezone_date": (
            datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
            datetime(2024, 7, 15, 12, 0, tzinfo=UTC),
        ),
    }
    if category not in builders:
        raise ValueError(f"unknown category: {category}")
    return builders[category]


def categories_for_db2_type(db2_type: str) -> tuple[str, ...]:
    """Pick categories that fit one Db2 column type."""
    upper = db2_type.upper()
    if "INT" in upper or "DECIMAL" in upper or upper in ("REAL", "DOUBLE"):
        return ("null", "extreme_int", "rounding_number")
    if "DATE" in upper or "TIME" in upper:
        return ("null", "dst_date", "timezone_date")
    if "CHAR" in upper or "BLOB" in upper:
        return (
            "null",
            "empty_string",
            "single_space",
            "trailing_space",
            "mixed_case",
            "unicode",
            "long_string",
        )
    return ("null",)
