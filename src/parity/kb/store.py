"""Knowledge base store.

Only verified entries are searchable. New fixes
start as candidates. A human approves or rejects
them. Only approved entries are shared.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from parity.kb.embeddings import HashingEmbedder, cosine_distance

KNOWN_DIFFERENCE_DDL = """CREATE TABLE known_difference (
    difference_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    source_pattern VARCHAR(2000) NOT NULL,
    db2_pattern VARCHAR(2000) NOT NULL,
    cause VARCHAR(2000),
    fix_template VARCHAR(2000),
    verified SMALLINT NOT NULL DEFAULT 0,
    evidence_run_id INTEGER,
    embedding VECTOR(384, FLOAT32)
)"""


@dataclass
class KnownDifference:
    """One known difference and its fix."""

    title: str
    source_pattern: str
    db2_pattern: str
    cause: str = ""
    fix_template: str = ""
    verified: bool = False
    evidence_run_id: int | None = None
    embedding: tuple[float, ...] = ()

    def search_text(self) -> str:
        """Text used for embedding and search."""
        return f"{self.title} {self.source_pattern} {self.cause}"


@dataclass(frozen=True)
class ScoredDifference:
    """One search hit with its distance."""

    entry: KnownDifference
    distance: float


class KbStore(Protocol):
    """Store interface for known differences."""

    def add(self, entry: KnownDifference) -> None:
        """Add one entry. Embeds it if needed."""
        ...

    def approve(self, title: str) -> None:
        """Mark one entry verified."""
        ...

    def reject(self, title: str) -> None:
        """Remove one unverified entry."""
        ...

    def search(self, query: str, limit: int = 5) -> tuple[ScoredDifference, ...]:
        """Search verified entries. Return closest first."""
        ...


class InMemoryKb:
    """Dict backed store. For tests and local runs."""

    def __init__(self, embedder: HashingEmbedder | None = None) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._entries: dict[str, KnownDifference] = {}

    def add(self, entry: KnownDifference) -> None:
        """Add one entry. Embeds it if needed."""
        if not entry.embedding:
            entry.embedding = self._embedder.embed(entry.search_text())
        self._entries[entry.title] = entry

    def approve(self, title: str) -> None:
        """Mark one entry verified."""
        if title not in self._entries:
            raise KeyError(f"unknown entry: {title}")
        self._entries[title].verified = True

    def reject(self, title: str) -> None:
        """Remove one unverified entry."""
        entry = self._entries.get(title)
        if entry is None:
            raise KeyError(f"unknown entry: {title}")
        if entry.verified:
            raise ValueError("verified entries cannot be rejected")
        del self._entries[title]

    def search(self, query: str, limit: int = 5) -> tuple[ScoredDifference, ...]:
        """Search verified entries. Return closest first."""
        query_vector = self._embedder.embed(query)
        scored = [
            ScoredDifference(entry, cosine_distance(query_vector, entry.embedding))
            for entry in self._entries.values()
            if entry.verified
        ]
        scored.sort(key=lambda item: item.distance)
        return tuple(scored[:limit])


class Db2Kb:
    """Db2 backed store using VECTOR_DISTANCE."""

    def __init__(self, admin, embedder: HashingEmbedder | None = None) -> None:
        self._admin = admin
        self._embedder = embedder or HashingEmbedder()

    def create_table(self) -> None:
        """Create the known_difference table."""
        self._admin.execute_ddl(KNOWN_DIFFERENCE_DDL)

    def add(self, entry: KnownDifference) -> None:
        """Add one entry with its embedding."""
        from parity.sync.db2_admin import Db2Admin

        if not isinstance(self._admin, Db2Admin):
            raise TypeError("Db2Kb needs a Db2Admin instance")
        if not entry.embedding:
            entry.embedding = self._embedder.embed(entry.search_text())
        import ibm_db

        conn = self._admin._connect()
        try:
            stmt = ibm_db.prepare(
                conn,
                "INSERT INTO known_difference "
                "(title, source_pattern, db2_pattern, cause, fix_template, verified, evidence_run_id, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, VECTOR(?, 384, FLOAT32))",
            )
            values = [
                entry.title,
                entry.source_pattern,
                entry.db2_pattern,
                entry.cause,
                entry.fix_template,
                1 if entry.verified else 0,
                entry.evidence_run_id,
            ]
            for index, value in enumerate(values, start=1):
                ibm_db.bind_param(stmt, index, value)
            vector_text = ",".join(f"{value:.6f}" for value in entry.embedding)
            ibm_db.bind_param(stmt, 8, vector_text)
            ibm_db.execute(stmt)
        finally:
            ibm_db.close(conn)

    def approve(self, title: str) -> None:
        """Mark one entry verified."""
        import ibm_db

        conn = self._admin._connect()
        try:
            stmt = ibm_db.prepare(
                conn, "UPDATE known_difference SET verified = 1 WHERE title = ?"
            )
            ibm_db.bind_param(stmt, 1, title)
            ibm_db.execute(stmt)
        finally:
            ibm_db.close(conn)

    def reject(self, title: str) -> None:
        """Remove one unverified entry."""
        import ibm_db

        conn = self._admin._connect()
        try:
            stmt = ibm_db.prepare(
                conn,
                "DELETE FROM known_difference WHERE title = ? AND verified = 0",
            )
            ibm_db.bind_param(stmt, 1, title)
            ibm_db.execute(stmt)
        finally:
            ibm_db.close(conn)

    def search(self, query: str, limit: int = 5) -> tuple[ScoredDifference, ...]:
        """Search verified entries with VECTOR_DISTANCE."""
        import ibm_db

        query_vector = self._embedder.embed(query)
        vector_text = ",".join(f"{value:.6f}" for value in query_vector)
        conn = self._admin._connect()
        try:
            stmt = ibm_db.prepare(
                conn,
                "SELECT title, source_pattern, db2_pattern, cause, fix_template, "
                "VECTOR_DISTANCE(embedding, VECTOR(?, 384, FLOAT32), COSINE) AS dist "
                "FROM known_difference WHERE verified = 1 ORDER BY dist FETCH FIRST ? ROWS ONLY",
            )
            ibm_db.bind_param(stmt, 1, vector_text)
            ibm_db.bind_param(stmt, 2, limit)
            ibm_db.execute(stmt)
            results: list[ScoredDifference] = []
            while True:
                row = ibm_db.fetch_tuple(stmt)
                if row is False or row is None:
                    break
                entry = KnownDifference(
                    title=row[0],
                    source_pattern=row[1],
                    db2_pattern=row[2],
                    cause=row[3] or "",
                    fix_template=row[4] or "",
                    verified=True,
                )
                results.append(ScoredDifference(entry, float(row[5])))
            return tuple(results)
        finally:
            ibm_db.close(conn)
