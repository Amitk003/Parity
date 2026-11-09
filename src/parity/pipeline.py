"""End to end run pipeline.

Ingest a directory of SQL files, translate each query,
compare on both databases, and collect report entries.
Schema and data sync happens before this step. The
pipeline assumes both databases already hold the
same data.

Translation is rules first. Queries the rules cannot
handle go to the optional gateway (an agent proposes,
the engine still decides). In replay mode the gateway
serves recorded responses only and never touches the
network.
"""

from __future__ import annotations

from pathlib import Path

from parity.agents.prompts import system_prompt
from parity.agents.types import AgentRole
from parity.engine.executor import DatabaseExecutor
from parity.engine.result import ComparisonResult, ComparisonStatus
from parity.gateway.client import Gateway
from parity.gateway.types import BudgetExceededError, CacheMissError
from parity.ingest.loader import deduplicate, load_sql_dir
from parity.report.risk import QueryReport
from parity.runner import run_comparison
from parity.translate.rules import translate


def quote_table(db2_sql: str, table: str | None) -> str:
    """Quote the source table name in the Db2 SQL."""
    if table:
        return db2_sql.replace(table, f'"{table.upper()}"', 1)
    return db2_sql


def _agent_translate(
    query_id: str, source_sql: str, gateway: Gateway
) -> tuple[str, str]:
    """Ask the gateway agent for Db2 SQL.

    Return (db2_sql, ""). On failure return ("", reason).
    """
    user = f"Translate this PostgreSQL query to Db2:\n{source_sql}"
    try:
        response = gateway.complete(
            "translator", system_prompt(AgentRole.TRANSLATOR), user
        )
    except CacheMissError:
        return "", f"{query_id}: replay cache miss, call was not recorded"
    except BudgetExceededError:
        return "", f"{query_id}: token budget exhausted"
    sql = response.text.strip()
    if not sql:
        return "", f"{query_id}: agent returned empty SQL"
    return sql, ""


def run_pipeline(
    workload_dir: Path,
    source: DatabaseExecutor,
    target: DatabaseExecutor,
    gateway: Gateway | None = None,
) -> list[QueryReport]:
    """Run the full pipeline. Return report entries."""
    queries = deduplicate(load_sql_dir(workload_dir))
    reports: list[QueryReport] = []
    for query in queries:
        if not query.read_only:
            result = ComparisonResult(
                status=ComparisonStatus.NOT_COMPARABLE,
                note="write query: not executed",
            )
            reports.append(
                QueryReport.from_result(query.query_id, query.source_sql, "", result)
            )
            continue
        translation = translate(query.source_sql)
        if translation.untranslatable:
            if gateway is None:
                result = ComparisonResult(
                    status=ComparisonStatus.NOT_COMPARABLE,
                    note="untranslatable by rules "
                    f"({', '.join(translation.untranslatable)}); "
                    "no agent gateway configured",
                )
                reports.append(
                    QueryReport.from_result(
                        query.query_id, query.source_sql, "", result
                    )
                )
                continue
            agent_sql, failure = _agent_translate(
                query.query_id, query.source_sql, gateway
            )
            if failure or not agent_sql:
                note = failure or "agent returned empty SQL"
                result = ComparisonResult(
                    status=ComparisonStatus.NOT_COMPARABLE,
                    note=f"agent translation failed: {note}",
                )
                reports.append(
                    QueryReport.from_result(
                        query.query_id, query.source_sql, "", result
                    )
                )
                continue
            db2_sql = quote_table(agent_sql, query.tables[0] if query.tables else None)
        else:
            db2_sql = quote_table(
                translation.db2_sql, query.tables[0] if query.tables else None
            )
        result = run_comparison(source, target, query.source_sql, db2_sql)
        reports.append(
            QueryReport.from_result(query.query_id, query.source_sql, db2_sql, result)
        )
    return reports
