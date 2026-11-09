"""Tests for CI workflow and the sample seed script."""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def workflow_text() -> str:
    path = ROOT / ".github" / "workflows" / "parity-ci.yml"
    return path.read_text(encoding="utf-8")


def test_workflow_file_exists():
    text = workflow_text()
    assert "name: parity-ci" in text
    assert "lint-test" in text
    assert "parity-live" in text


def test_workflow_runs_lint_and_tests():
    text = workflow_text()
    assert "ruff check src tests" in text
    assert "pytest -q" in text
    assert 'python-version: "3.11"' in text


def test_workflow_live_job_uses_bridge_and_run():
    text = workflow_text()
    assert "Dockerfile.bridge" in text
    assert "seed_sample.py" in text
    assert "python -m parity.cli run" in text
    assert "--bridge" in text


def test_workflow_has_no_secrets():
    text = workflow_text().lower()
    assert "api_key" not in text
    assert "BEGIN PRIVATE" not in text


def test_seed_script_reuses_parity_sync():
    seed = (ROOT / "scripts" / "seed_sample.py").read_text(encoding="utf-8")
    assert "from parity.sync" in seed
    assert "copy_table" in seed
    assert "checksum" in seed
    assert "demo_users" in seed
