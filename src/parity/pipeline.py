"""End to end run pipeline.

Ingest a directory of SQL files, translate each query,
compare on both databases, and collect report entries.
Schema and data sync happens before this step. The
pipeline assumes both databases already hold the
same data.
"""

from __future__ import annotations

from pathlib import Path

from parity.engine.executor import DatabaseExecutor
from parity.ingest.loader import deduplicate, load_sql_dir
from parity.report.risk import QueryReport
from parity.runner import run_comparison
from parity.translate.rules import translate


def run_pipeline(
    workload_dir: Path,
    source: DatabaseExecutor,
    target: DatabaseExecutor,
) -> list[QueryReport]:
    """Run the full pipeline. Return report entries."""
    queries = deduplicate(load_sql_dir(workload_dir))
    reports: list[QueryReport] = []
    for query in queries:
        if not query.read_only:
            from parity.engine.result import ComparisonResult, ComparisonStatus

            result = ComparisonResult(
                status=ComparisonStatus.NOT_COMPARABLE,
                note="write query: not executed",
            )
            reports.append(
                QueryReport.from_result(query.query_id, query.source_sql, "", result)
            )
            continue
        translated = translate(query.source_sql)
        db2_sql = translated.db2_sql.replace(query.tables[0], f'"{query.tables[0].upper()}"', 1) if query.tables else translated.db2_sql
        result = run_comparison(source, target, query.source_sql, db2_sql)
        reports.append(
            QueryReport.from_result(query.query_id, query.source_sql, db2_sql, result)
        )
    return reports
