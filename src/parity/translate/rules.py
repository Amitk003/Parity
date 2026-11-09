"""Rule based Postgres to Db2 rewrites.

Each rule is a small regex rewrite with a name. Rules
run in order. Every change is recorded so a reviewer
can see exactly what was rewritten and why.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from parity.translate.result import TranslationResult

_CAST_TYPES = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "text": "VARCHAR(4000)",
    "varchar": "VARCHAR(255)",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
    "numeric": "DECIMAL(18, 6)",
    "decimal": "DECIMAL(18, 6)",
    "real": "REAL",
    "double precision": "DOUBLE",
}

_UNTRANSLATABLE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("json_arrow_operator", re.compile(r"->>?")),
    ("regex_operator", re.compile(r"[^<>=!~]~\*?")),
    ("array_literal", re.compile(r"ARRAY\s*\[", re.IGNORECASE)),
    ("returning_clause", re.compile(r"\bRETURNING\b", re.IGNORECASE)),
    ("dollar_quoting", re.compile(r"\$\$")),
    ("serial_type", re.compile(r"\bSERIAL\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class Rule:
    """One rewrite rule."""

    name: str
    pattern: re.Pattern[str]
    replace: str | Callable[[re.Match[str]], str]


def _cast_repl(match: re.Match[str]) -> str:
    expr = match.group(1)
    raw_type = match.group(2).strip().lower()
    db2_type = _CAST_TYPES.get(raw_type, raw_type.upper())
    return f"CAST({expr} AS {db2_type})"


def _limit_repl(match: re.Match[str]) -> str:
    limit = match.group(1)
    offset = match.group(2)
    if offset:
        return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
    return f"FETCH FIRST {limit} ROWS ONLY"


_RULES: tuple[Rule, ...] = (
    Rule(
        name="cast_double_colon",
        pattern=re.compile(r"(\S+?)::\s*([a-zA-Z ]+)"),
        replace=_cast_repl,
    ),
    Rule(
        name="ilike_to_upper_like",
        pattern=re.compile(r"(\S+)\s+ILIKE\s+(\S+)", re.IGNORECASE),
        replace=lambda m: f"UPPER({m.group(1)}) LIKE UPPER({m.group(2)})",
    ),
    Rule(
        name="limit_offset_to_fetch",
        pattern=re.compile(r"LIMIT\s+(\d+)(?:\s+OFFSET\s+(\d+))?", re.IGNORECASE),
        replace=_limit_repl,
    ),
    Rule(
        name="now_to_current_timestamp",
        pattern=re.compile(r"\bnow\s*\(\s*\)", re.IGNORECASE),
        replace="CURRENT_TIMESTAMP",
    ),
    Rule(
        name="random_to_rand",
        pattern=re.compile(r"\brandom\s*\(\s*\)", re.IGNORECASE),
        replace="RAND()",
    ),
    Rule(
        name="substring_from_to_comma",
        pattern=re.compile(
            r"SUBSTRING\s*\(\s*(.+?)\s+FROM\s+(\d+)(?:\s+FOR\s+(\d+))?\s*\)",
            re.IGNORECASE,
        ),
        replace=lambda m: (
            f"SUBSTRING({m.group(1)}, {m.group(2)}, {m.group(3)})"
            if m.group(3)
            else f"SUBSTRING({m.group(1)}, {m.group(2)})"
        ),
    ),
)


def list_rules() -> tuple[str, ...]:
    """Return rule names in run order."""
    return tuple(rule.name for rule in _RULES)


def find_untranslatable(sql: str) -> tuple[str, ...]:
    """Return names of patterns with no known Db2 form."""
    return tuple(name for name, pattern in _UNTRANSLATABLE if pattern.search(sql))


def translate(sql: str) -> TranslationResult:
    """Translate one Postgres statement to Db2 SQL.

    Rules apply in order. The result records which
    rules fired and which patterns need a human.
    """
    if not sql or not sql.strip():
        raise ValueError("empty SQL")
    result = sql.strip()
    applied: list[str] = []
    for rule in _RULES:
        new_text, count = rule.pattern.subn(rule.replace, result)
        if count:
            applied.append(rule.name)
            result = new_text
    return TranslationResult(
        db2_sql=result,
        applied_rules=tuple(applied),
        untranslatable=find_untranslatable(result),
    )
