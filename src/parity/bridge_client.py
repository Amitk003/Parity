"""Bridge client. Runs inside a Linux container.

Reads one SQL statement from stdin, runs it on Db2
with ibm_db, and writes the result as JSON to stdout.
Values are encoded as text so dates and decimals
survive the trip. NULL stays JSON null.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def encode_value(value: Any) -> Any:
    """Encode one cell value for JSON transport."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def run_and_encode(sql: str, settings) -> dict[str, Any]:
    """Run SQL on Db2. Return a JSON safe dict."""
    import ibm_db

    from parity.engine.db2 import _connection_string

    conn = ibm_db.connect(_connection_string(settings), "", "")
    try:
        stmt = ibm_db.exec_immediate(conn, sql)
        columns = [
            ibm_db.result_column_name(stmt, i)
            for i in range(1, ibm_db.num_fields(stmt) + 1)
        ]
        rows: list[list[Any]] = []
        while True:
            row = ibm_db.fetch_tuple(stmt)
            if row is False or row is None:
                break
            rows.append([encode_value(value) for value in row])
        return {"columns": columns, "rows": rows}
    finally:
        ibm_db.close(conn)


def main() -> int:
    """Read SQL from stdin. Write JSON to stdout."""
    sql = sys.stdin.read().strip()
    if not sql:
        print(json.dumps({"error": "empty SQL on stdin"}))
        return 2
    from parity.config import load_settings

    _, db2_settings = load_settings()
    try:
        result = run_and_encode(sql, db2_settings)
    except Exception as exc:  # noqa: BLE001 - any Db2 failure becomes error JSON
        print(json.dumps({"error": str(exc)[:500]}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
