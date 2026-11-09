"""Command line entry point.

Usage:
    parity compare --source-sql "SELECT 1" --target-sql "SELECT 1"
    parity run --dir samples --out report.html
    parity kb-review --action list

Exit codes:
    0 - MATCH or all queries passed
    1 - MISMATCH
    2 - ERROR or NOT_COMPARABLE
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parity.config import load_settings
from parity.engine.db2 import Db2Executor
from parity.engine.db2_bridge import Db2BridgeExecutor
from parity.engine.postgres import PostgresExecutor
from parity.engine.result import ComparisonStatus
from parity.history.json_store import JsonRunStore
from parity.history.store import save_run
from parity.kb.review import run_review
from parity.kb.store import Db2Kb, InMemoryKb
from parity.pipeline import run_pipeline
from parity.report.html import render_html, render_json_summary
from parity.runner import run_comparison

_EXIT_CODES = {
    ComparisonStatus.MATCH: 0,
    ComparisonStatus.MISMATCH: 1,
    ComparisonStatus.ERROR: 2,
    ComparisonStatus.NOT_COMPARABLE: 2,
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="parity", description="Parity SQL comparison")
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare", help="Compare one query on two databases")
    compare.add_argument("--source-sql", required=True)
    compare.add_argument("--target-sql", required=True)
    compare.add_argument("--timeout", type=float, default=30.0)
    run = sub.add_parser("run", help="Run a workload directory and write a report")
    run.add_argument("--dir", required=True, help="Directory with .sql files")
    run.add_argument("--out", default="parity-report.html", help="HTML report path")
    run.add_argument("--json-out", default="", help="Optional JSON summary path")
    run.add_argument("--history", default="", help="Optional run history file path")
    run.add_argument("--bridge", action="store_true", help="Use the Linux bridge for Db2")
    kb = sub.add_parser("kb-review", help="Review knowledge base candidates")
    kb.add_argument("--action", required=True, choices=("list", "approve", "reject"))
    kb.add_argument("--title", default="", help="Entry title for approve and reject")
    kb.add_argument("--store", choices=("memory", "db2"), default="memory")
    return parser


def _run_compare(args) -> int:
    source_settings, db2_settings = load_settings()
    source = PostgresExecutor(source_settings)
    target = Db2Executor(db2_settings)
    result = run_comparison(
        source,
        target,
        source_sql=args.source_sql,
        target_sql=args.target_sql,
        timeout_seconds=args.timeout,
    )
    print(f"status: {result.status.value}")
    if result.note:
        print(f"note: {result.note}")
    for diff in result.diffs:
        print(f"diff: {diff.kind.value} {diff.detail}")
    return _EXIT_CODES[result.status]


def _pipeline_exit_code(reports) -> int:
    """Exit code for a pipeline run: 0 all match, 1 any mismatch, 2 otherwise."""
    statuses = [report.result.status for report in reports]
    if all(status is ComparisonStatus.MATCH for status in statuses):
        return 0
    if any(status is ComparisonStatus.MISMATCH for status in statuses):
        return 1
    return 2


def _run_pipeline(args) -> int:
    source_settings, db2_settings = load_settings()
    source = PostgresExecutor(source_settings)
    if args.bridge:
        target = Db2BridgeExecutor(db2_settings)
    else:
        target = Db2Executor(db2_settings)
    reports = run_pipeline(Path(args.dir), source, target)
    exit_code = _pipeline_exit_code(reports)
    run_id: int | None = None
    if args.history:
        store = JsonRunStore(Path(args.history))
        run_id = save_run(store, args.dir, reports, exit_code)
        print(f"history written: {args.history} (run id {run_id})")
    title = f"Parity report (run id {run_id})" if run_id is not None else "Parity report"
    Path(args.out).write_text(render_html(reports, title=title), encoding="utf-8")
    print(f"report written: {args.out}")
    if args.json_out:
        Path(args.json_out).write_text(
            render_json_summary(reports, run_id=run_id), encoding="utf-8"
        )
        print(f"summary written: {args.json_out}")
    return exit_code


def _run_kb_review(args) -> int:
    _, db2_settings = load_settings()
    if args.store == "db2":
        from parity.sync.db2_admin import Db2Admin

        store = Db2Kb(Db2Admin(db2_settings))
    else:
        store = InMemoryKb()
    try:
        print(run_review(store, args.action, args.title))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary turns any error into exit 2
        print(f"error: {exc}")
        return 2


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Return the exit code."""
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _run_pipeline(args)
    if args.command == "kb-review":
        return _run_kb_review(args)
    return _run_compare(args)


if __name__ == "__main__":
    sys.exit(main())
