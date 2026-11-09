"""Fuzz plan and row generation.

A FuzzPlan says which edge case values to use for
each column of one table. Generation is seeded, so
the same plan always makes the same rows.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from parity.fuzz.values import categories_for_db2_type, values_for_category
from parity.sync.schema import TableDef


@dataclass(frozen=True)
class ColumnFuzz:
    """Edge values for one column."""

    column: str
    categories: tuple[str, ...]
    values: tuple[Any, ...]


@dataclass(frozen=True)
class FuzzPlan:
    """Full fuzz plan for one table."""

    table: str
    columns: tuple[ColumnFuzz, ...]
    seed: int = 42

    @property
    def plan_id(self) -> str:
        """Stable id for this plan."""
        raw = f"{self.table}:{self.seed}:" + ",".join(
            f"{c.column}={','.join(c.categories)}" for c in self.columns
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build_plan(table: TableDef, seed: int = 42) -> FuzzPlan:
    """Build a plan from a table definition."""
    columns: list[ColumnFuzz] = []
    for col in table.columns:
        categories = categories_for_db2_type(col.db2_type)
        values: list[Any] = []
        for category in categories:
            values.extend(values_for_category(category))
        columns.append(
            ColumnFuzz(column=col.name, categories=categories, values=tuple(values))
        )
    return FuzzPlan(table=table.name, columns=tuple(columns), seed=seed)


def generate_rows(plan: FuzzPlan, base_row: tuple[Any, ...], count: int) -> list[tuple[Any, ...]]:
    """Generate fuzz rows from a base row.

    Each row starts as a copy of the base row, then
    one or two columns get edge values. The seed
    makes the output repeatable.
    """
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(plan.seed)
    rows: list[tuple[Any, ...]] = []
    width = len(plan.columns)
    for _ in range(count):
        row = list(base_row)
        picks = rng.sample(range(width), k=min(2, width))
        for index in picks:
            values = plan.columns[index].values
            if values:
                row[index] = rng.choice(values)
        rows.append(tuple(row))
    return rows


def plan_to_dict(plan: FuzzPlan) -> dict[str, Any]:
    """Return a JSON safe dict for storage and logs."""
    return {
        "plan_id": plan.plan_id,
        "table": plan.table,
        "seed": plan.seed,
        "columns": [
            {
                "column": col.column,
                "categories": list(col.categories),
                "value_count": len(col.values),
            }
            for col in plan.columns
        ],
    }
