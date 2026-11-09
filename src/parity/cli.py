"""Command line entry point.

Usage:
    parity compare --source-sql "SELECT 1" --target-sql "SELECT 1"

Exit codes:
    0 - MATCH
    1 - MISMATCH
    2 - ERROR or NOT_COMPARABLE
"""

from __future__ import annotations

import argparse
import sys

from parity.config import load_settings
from parity.engine.db2 import Db2Executor
from parity.engine.postgres import PostgresExecutor
from parity.engine.result import ComparisonStatus
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Return the exit code."""
    args = build_parser().parse_args(argv)
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


if __name__ == "__main__":
    sys.exit(main())
