"""Tests for schemas."""

import pytest

from aigis.schemas import CheckResult, HealthReport, Severity


def test_severity_order() -> None:
    """Severity enum values are comparable."""
    assert Severity.CRITICAL.value == "CRITICAL"
    assert Severity.WARN.value == "WARN"
    assert Severity.OK.value == "OK"


def test_check_result_serialization() -> None:
    """CheckResult serializes to JSON."""
    c = CheckResult(
        check_id="test",
        name="Test check",
        severity=Severity.OK,
        message="OK",
    )
    assert c.model_dump()["severity"] == "OK"


def test_health_report_build() -> None:
    """HealthReport builds with checks."""
    r = HealthReport(
        run_id="abc",
        overall_severity=Severity.OK,
        checks=[
            CheckResult(check_id="x", name="X", severity=Severity.OK, message="OK"),
        ],
    )
    assert r.overall_severity == Severity.OK
    assert len(r.checks) == 1
