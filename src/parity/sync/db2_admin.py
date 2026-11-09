"""Db2 admin client for sync operations.

This client can run DDL and DML. It is used only on
the disposable test database. It is never used for
the read only workload queries. Those go through
Db2Executor and the safety guard.
"""

from __future__ import annotations

from parity.config import DatabaseSettings
from parity.engine.db2 import _connection_string
from parity.sync.schema import TableDef, build_create_table


class Db2Admin:
    """Run DDL and DML on Db2 test schema."""

    def __init__(self, settings: DatabaseSettings) -> None:
        settings.require_complete("Db2")
        self._settings = settings

    def _connect(self):
        import ibm_db

        return ibm_db.connect(_connection_string(self._settings), "", "")

    def execute_ddl(self, sql: str) -> None:
        """Run one DDL statement. Raise on error."""
        import ibm_db

        conn = self._connect()
        try:
            ibm_db.exec_immediate(conn, sql)
        finally:
            ibm_db.close(conn)

    def create_tables(self, tables: tuple[TableDef, ...]) -> None:
        """Create each table. Existing tables raise an error."""
        for table in tables:
            self.execute_ddl(build_create_table(table))

    def table_exists(self, name: str) -> bool:
        """True when a table with this name exists."""
        import ibm_db

        conn = self._connect()
        try:
            stmt = ibm_db.prepare(
                conn,
                "SELECT COUNT(*) FROM SYSCAT.TABLES WHERE TABNAME = ?",
            )
            ibm_db.bind_param(stmt, 1, name.upper())
            ibm_db.execute(stmt)
            row = ibm_db.fetch_tuple(stmt)
            return bool(row) and int(row[0]) > 0
        finally:
            ibm_db.close(conn)

    def drop_tables(self, tables: tuple[TableDef, ...]) -> None:
        """Drop each table if it exists. Used for clean reruns."""
        import ibm_db

        conn = self._connect()
        try:
            for table in tables:
                name = table.name.upper()
                stmt = ibm_db.prepare(conn, "SELECT COUNT(*) FROM SYSCAT.TABLES WHERE TABNAME = ?")
                ibm_db.bind_param(stmt, 1, name)
                ibm_db.execute(stmt)
                row = ibm_db.fetch_tuple(stmt)
                count = int(row[0]) if row else 0
                if count > 0:
                    ibm_db.exec_immediate(conn, f'DROP TABLE "{name}"')
        finally:
            ibm_db.close(conn)

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple]) -> None:
        """Insert rows with bound parameters. No string built values."""
        import ibm_db

        if not rows:
            return
        col_sql = ", ".join(f'"{c.upper()}"' for c in columns)
        marks = ", ".join("?" for _ in columns)
        sql = f'INSERT INTO "{table.upper()}" ({col_sql}) VALUES ({marks})'
        conn = self._connect()
        try:
            stmt = ibm_db.prepare(conn, sql)
            for row in rows:
                for index, value in enumerate(row, start=1):
                    ibm_db.bind_param(stmt, index, value)
                ibm_db.execute(stmt)
        finally:
            ibm_db.close(conn)
