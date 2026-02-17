"""Tests for rule engine."""

from aigis.config import AppConfig
from aigis.engine import run_rules
from aigis.schemas.checks import Severity
from aigis.schemas.signals import CollectorRun


def test_run_rules_returns_checks() -> None:
    """run_rules returns list of CheckResult."""
    runs: list[CollectorRun] = []
    config = AppConfig()
    checks = run_rules(runs, config)
    assert len(checks) >= 1
    assert all(c.severity in Severity for c in checks)


def test_run_rules_handles_empty_context() -> None:
    """run_rules handles missing collector data."""
    runs = [
        CollectorRun(collector_id="restic", success=False, error_message="failed"),
    ]
    config = AppConfig()
    checks = run_rules(runs, config)
    assert any(c.severity == Severity.WARN for c in checks)
