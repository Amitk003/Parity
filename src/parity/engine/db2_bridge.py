"""Db2 executor through a Linux container bridge.

The Windows ibm_db driver fails with SQL1042C. This
executor runs the same driver inside a Linux container
instead. It shells out to docker run, sends SQL on
stdin, and reads JSON on stdout.

Parity already needs Docker for the databases, so
this adds no new requirement.
"""

from __future__ import annotations

import json
import os
import subprocess

from parity.config import DatabaseSettings
from parity.engine.result import ResultSet
from parity.engine.safety import assert_read_only

_DEFAULT_IMAGE = "parity-bridge:latest"
_DEFAULT_ROW_LIMIT = 100_000


class Db2BridgeExecutor:
    """Execute read queries on Db2 via a Linux container."""

    def __init__(
        self,
        settings: DatabaseSettings,
        image: str = _DEFAULT_IMAGE,
        row_limit: int = _DEFAULT_ROW_LIMIT,
    ) -> None:
        settings.require_complete("Db2")
        if row_limit <= 0:
            raise ValueError("row_limit must be positive")
        self._settings = settings
        self._image = image
        self._row_limit = row_limit

    def _docker_command(self) -> list[str]:
        env_args: list[str] = []
        for name in (
            "PARITY_DB2_HOST",
            "PARITY_DB2_PORT",
            "PARITY_DB2_USER",
            "PARITY_DB2_PASSWORD",
            "PARITY_DB2_DB",
        ):
            value = os.environ.get(name, "")
            if value:
                env_args.extend(["-e", f"{name}={value}"])
        return [
            "docker",
            "run",
            "--rm",
            "-i",
            "--add-host=host.docker.internal:host-gateway",
            *env_args,
            self._image,
            "python",
            "-m",
            "parity.bridge_client",
        ]

    def execute(self, sql: str, timeout_seconds: float = 60.0) -> ResultSet:
        """Run SQL through the bridge. Return the result set."""
        assert_read_only(sql)
        completed = subprocess.run(
            self._docker_command(),
            input=sql,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"bridge failed: {completed.stderr.strip()[:300]}")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"bridge returned bad JSON: {exc}") from exc
        if "error" in payload:
            raise RuntimeError(f"bridge error: {payload['error']}")
        rows = [tuple(row) for row in payload["rows"]]
        if len(rows) > self._row_limit:
            raise ValueError(f"result exceeds row limit of {self._row_limit}")
        return ResultSet(columns=tuple(payload["columns"]), rows=tuple(rows))
