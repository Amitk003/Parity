"""Deterministic result comparison.

This module is the only judge in Parity. It compares two
result sets and returns MATCH or MISMATCH. It never calls
a model. It never guesses.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from parity.engine.normalize import is_trailing_space_only, normalize_value
from parity.engine.result import (
    ComparisonResult,
    ComparisonStatus,
    DiffKind,
    ResultSet,
    RowDiff,
)

_ORDER_BY = re.compile(r"\border\s+by\b", re.IGNORECASE)


@dataclass(frozen=True)
class EngineConfig:
    """Settings for one comparison run.

    float_tolerance is a relative tolerance for float values.
    Decimal and int values always need an exact match.
    """

    float_tolerance: float = 1e-9
    ignore_row_order: bool | None = None

    def __post_init__(self) -> None:
        if self.float_tolerance < 0:
            raise ValueError("float_tolerance cannot be negative")


def query_has_order_by(sql: str) -> bool:
    """True when the SQL text has an ORDER BY clause."""
    return bool(_ORDER_BY.search(sql))


def _settings(config: EngineConfig, order_matters: bool) -> tuple[tuple[str, str], ...]:
    return (
        ("float_tolerance", repr(config.float_tolerance)),
        ("row_order_matters", str(order_matters)),
    )


def _values_equal(left: Any, right: Any, tolerance: float) -> tuple[bool, DiffKind | None]:
    """Compare two normalized values. Return equal flag and diff kind."""
    if left is None and right is None:
        return True, None
    if left is None or right is None:
        return False, DiffKind.NULL_VS_VALUE
    if type(left) is not type(right):
        if isinstance(left, Decimal) and isinstance(right, float):
            pass
        elif isinstance(left, float) and isinstance(right, Decimal):
            pass
        else:
            return False, DiffKind.TYPE
    if isinstance(left, float) or isinstance(right, float):
        left_f = float(left)
        right_f = float(right)
        if math.isnan(left_f) and math.isnan(right_f):
            return True, None
        scale = max(1.0, abs(left_f), abs(right_f))
        if abs(left_f - right_f) <= tolerance * scale:
            return True, None
        return False, DiffKind.VALUE
    if left == right:
        return True, None
    if is_trailing_space_only(left, right):
        return False, DiffKind.TRAILING_SPACE
    return False, DiffKind.VALUE


def _row_key(row: tuple[Any, ...]) -> tuple[Any, ...]:
    """Stable sort key. None sorts first. Mixed types use text form."""
    key: list[Any] = []
    for value in row:
        if value is None:
            key.append((0, ""))
        elif isinstance(value, Decimal):
            key.append((1, str(value)))
        elif isinstance(value, bool):
            key.append((1, str(value)))
        else:
            key.append((1, str(value)))
    return tuple(key)


def _normalize_rows(result: ResultSet) -> list[tuple[Any, ...]]:
    return [tuple(normalize_value(v) for v in row) for row in result.rows]


def compare_result_sets(
    source: ResultSet,
    target: ResultSet,
    config: EngineConfig | None = None,
    sql: str = "",
) -> ComparisonResult:
    """Compare two result sets. Return the verdict and first diffs.

    Column names compare without case. Column order must match.
    Row order is ignored unless the query has ORDER BY. When
    order is ignored, rows compare as a multiset so duplicate
    rows count.
    """
    cfg = config or EngineConfig()
    order_matters = query_has_order_by(sql) if cfg.ignore_row_order is None else not cfg.ignore_row_order
    settings = _settings(cfg, order_matters)
    diffs: list[RowDiff] = []

    if len(source.columns) != len(target.columns):
        diffs.append(
            RowDiff(
                kind=DiffKind.COLUMN_COUNT,
                detail=f"source has {len(source.columns)} columns, target has {len(target.columns)}",
            )
        )
        return ComparisonResult(ComparisonStatus.MISMATCH, tuple(diffs), settings)

    for index, (left, right) in enumerate(zip(source.columns, target.columns)):
        if left.lower() != right.lower():
            diffs.append(
                RowDiff(
                    kind=DiffKind.COLUMN_NAME,
                    detail=f"column {index} name differs",
                    column=left,
                    source_value=left,
                    target_value=right,
                )
            )

    source_rows = _normalize_rows(source)
    target_rows = _normalize_rows(target)

    if len(source_rows) != len(target_rows):
        diffs.append(
            RowDiff(
                kind=DiffKind.ROW_COUNT,
                detail=f"source has {len(source_rows)} rows, target has {len(target_rows)}",
                source_value=len(source_rows),
                target_value=len(target_rows),
            )
        )

    if order_matters:
        pairs = list(zip(source_rows, target_rows))
    else:
        pairs = list(zip(sorted(source_rows, key=_row_key), sorted(target_rows, key=_row_key)))

    for row_index, (left_row, right_row) in enumerate(pairs):
        for col_index, column in enumerate(source.columns):
            equal, kind = _values_equal(
                left_row[col_index], right_row[col_index], cfg.float_tolerance
            )
            if not equal:
                diffs.append(
                    RowDiff(
                        kind=kind or DiffKind.VALUE,
                        detail=f"row {row_index} column {column} differs",
                        row_index=row_index,
                        column=column,
                        source_value=left_row[col_index],
                        target_value=right_row[col_index],
                    )
                )
                break
        if len(diffs) >= 5:
            break

    if diffs:
        return ComparisonResult(ComparisonStatus.MISMATCH, tuple(diffs), settings)
    return ComparisonResult(ComparisonStatus.MATCH, (), settings)
