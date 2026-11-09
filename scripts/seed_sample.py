"""Seed the sample workload into Postgres and Db2.

Runs inside a Linux container where ibm_db works. Used
by CI and by anyone who wants a clean sample run.
"""

from __future__ import annotations

import os

SEED_SQL = """
CREATE TABLE IF NOT EXISTS demo_users (id INTEGER, name VARCHAR(50))
"""


def main() -> int:
    """Seed Postgres, sync schema and data to Db2, verify checksums."""
    import psycopg

    from parity.config import load_settings
    from parity.sync.data import checksum_rows, copy_table, read_postgres_rows
    from parity.sync.db2_admin import Db2Admin
    from parity.sync.schema import build_create_table, introspect_postgres

    source, db2_settings = load_settings()
    conn = psycopg.connect(
        host=os.environ.get("PARITY_SOURCE_HOST", "localhost"),
        dbname=source.database,
        user=source.user,
        password=source.password,
        autocommit=True,
    )
    cur = conn.cursor()
    cur.execute(SEED_SQL)
    cur.execute("DELETE FROM demo_users")
    cur.execute("INSERT INTO demo_users VALUES (1, 'alice'), (2, 'bob'), (3, NULL)")
    conn.close()

    tables = introspect_postgres(source)
    demo = next(table for table in tables if table.name == "demo_users")
    print("ddl:", build_create_table(demo))
    admin = Db2Admin(db2_settings)
    admin.drop_tables((demo,))
    admin.create_tables((demo,))
    count, src_sum, _ = copy_table(source, admin, demo)
    rows = read_postgres_rows(source, demo)
    assert checksum_rows(rows) == src_sum
    print(f"seeded {count} rows, checksum {src_sum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
