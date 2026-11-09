"""PostgreSQL to Db2 type mapping.

Unknown types raise ValueError. Parity never guesses
a type, because a wrong type can change query results.
"""

from __future__ import annotations

_TYPE_MAP: dict[str, str] = {
    "smallint": "SMALLINT",
    "integer": "INTEGER",
    "int": "INTEGER",
    "bigint": "BIGINT",
    "boolean": "BOOLEAN",
    "real": "REAL",
    "double precision": "DOUBLE",
    "numeric": "DECIMAL(18, 6)",
    "decimal": "DECIMAL(18, 6)",
    "money": "DECIMAL(18, 6)",
    "character varying": "VARCHAR(255)",
    "varchar": "VARCHAR(255)",
    "character": "CHAR(255)",
    "char": "CHAR(255)",
    "text": "VARCHAR(4000)",
    "date": "DATE",
    "time without time zone": "TIME",
    "time with time zone": "TIME WITH TIME ZONE",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMP WITH TIME ZONE",
    "timestamp": "TIMESTAMP",
    "uuid": "VARCHAR(36)",
    "bytea": "BLOB(1MB)",
    "json": "VARCHAR(4000)",
    "jsonb": "VARCHAR(4000)",
}


def map_type(postgres_type: str) -> str:
    """Map one PostgreSQL type name to a Db2 type."""
    key = postgres_type.strip().lower()
    if key in _TYPE_MAP:
        return _TYPE_MAP[key]
    if key.startswith("character varying"):
        return "VARCHAR(255)"
    if key.startswith("numeric") or key.startswith("decimal"):
        return "DECIMAL(18, 6)"
    raise ValueError(f"no Db2 mapping for type: {postgres_type}")


def supported_types() -> tuple[str, ...]:
    """Return sorted known PostgreSQL type names."""
    return tuple(sorted(_TYPE_MAP))
