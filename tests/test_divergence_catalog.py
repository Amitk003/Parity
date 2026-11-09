"""Tests for the divergence catalog and golden probe suite."""

from pathlib import Path

from parity.ingest.loader import load_sql_file

ROOT = Path(__file__).parent.parent


def catalog_text() -> str:
    return (ROOT / "docs" / "divergence-catalog.md").read_text(encoding="utf-8")


def test_catalog_lists_confirmed_divergences():
    text = catalog_text()
    assert "Unaliased aggregate column name" in text
    assert "Trailing space and Unicode text" in text
    assert "SELECT without FROM" in text
    assert "SQL0104N" in text
    assert "Expression SELECTs without FROM" in text
    assert "Unaliased scalar expression column name" in text
    assert "Matched probes" in text


def test_catalog_marks_hypotheses():
    text = catalog_text()
    assert "Hypotheses still to confirm" in text
    assert "Do not quote them as facts" in text


def test_probe_suite_loads():
    queries = load_sql_file(ROOT / "samples" / "probes.sql")
    assert len(queries) >= 14
    assert all(query.read_only for query in queries)


def test_probe_suite_covers_catalog_queries():
    queries = load_sql_file(ROOT / "samples" / "probes.sql")
    sqls = [query.source_sql for query in queries]
    assert "SELECT COUNT(*) FROM demo_users" in sqls
    assert "SELECT 1" in sqls
    assert "SELECT UPPER(name) FROM demo_users WHERE id = 1" in sqls
