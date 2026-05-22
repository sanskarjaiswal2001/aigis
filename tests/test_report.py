"""Tests for report builder and markdown renderer."""

from aigis.report.builder import build_report, _overall_severity
from aigis.report.markdown import render_markdown
from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.signals import CollectorRun, DiskSignal



class TestOverallSeverity:
    """Tests for _overall_severity helper."""

    def test_ok_when_empty(self) -> None:
        assert _overall_severity([]) == Severity.OK

    def test_ok_when_all_ok(self) -> None:
        checks = [
            CheckResult(check_id="a", name="A", severity=Severity.OK, message="ok"),
            CheckResult(check_id="b", name="B", severity=Severity.OK, message="ok"),
        ]
        assert _overall_severity(checks) == Severity.OK

    def test_warn_propagates(self) -> None:
        checks = [
            CheckResult(check_id="a", name="A", severity=Severity.OK, message="ok"),
            CheckResult(check_id="b", name="B", severity=Severity.WARN, message="warn"),
        ]
        assert _overall_severity(checks) == Severity.WARN

    def test_critical_dominates(self) -> None:
        checks = [
            CheckResult(check_id="a", name="A", severity=Severity.WARN, message="warn"),
            CheckResult(check_id="b", name="B", severity=Severity.CRITICAL, message="crit"),
        ]
        assert _overall_severity(checks) == Severity.CRITICAL


class TestBuildReport:
    """Tests for build_report."""

    def test_basic_report(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.OK, message="ok")]
        report = build_report(checks=checks)
        assert report.run_id
        assert report.overall_severity == Severity.OK
        assert len(report.checks) == 1

    def test_with_explanation(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.WARN, message="high")]
        report = build_report(
            checks=checks,
            anomaly_explanation="Disk is filling up",
            reasoning_trace="Checked thresholds",
        )
        assert report.anomaly_explanation == "Disk is filling up"
        assert report.reasoning_trace == "Checked thresholds"
        assert report.overall_severity == Severity.WARN

    def test_with_detected_issues(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.CRITICAL, message="crit")]
        issues = [{"component": "disk", "severity": "CRITICAL", "explanation": "full"}]
        report = build_report(checks=checks, detected_issues=issues)
        assert report.detected_issues == issues

    def test_with_manual_recommendations(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.OK, message="ok")]
        recs = [{"description": "Run fsck", "risk_level": "medium"}]
        report = build_report(checks=checks, manual_recommendations=recs)
        assert report.manual_recommendations == recs

    def test_with_collector_runs(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.OK, message="ok")]
        runs = [
            CollectorRun(
                collector_id="disk",
                success=True,
                signals=[DiskSignal(mount_point="/", total_gb=100.0, used_gb=50.0, used_pct=50.0)],
            ),
        ]
        report = build_report(checks=checks, collector_runs=runs)
        assert "disk" in report.collected_metrics
        assert len(report.collected_metrics["disk"]) == 1

    def test_with_metadata(self) -> None:
        checks = []
        report = build_report(checks=checks, metadata={"duration_ms": 123})
        assert report.metadata["duration_ms"] == 123


class TestRenderMarkdown:
    """Tests for render_markdown."""

    def test_renders_header(self) -> None:
        report = build_report(
            checks=[CheckResult(check_id="x", name="X", severity=Severity.OK, message="ok")],
        )
        md = render_markdown(report)
        assert "AIgis Health Report" in md
        assert report.run_id in md

    def test_renders_checks_table(self) -> None:
        checks = [
            CheckResult(check_id="disk", name="Disk Usage", severity=Severity.WARN, message="85% used"),
            CheckResult(check_id="load", name="Load", severity=Severity.OK, message="normal"),
        ]
        report = build_report(checks=checks)
        md = render_markdown(report)
        assert "Disk Usage" in md
        assert "85% used" in md
        assert "| Status | Check | Message |" in md

    def test_renders_explanation(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.WARN, message="w")]
        report = build_report(checks=checks, anomaly_explanation="The disk is filling up fast.")
        md = render_markdown(report)
        assert "## Analysis" in md
        assert "disk is filling up" in md

    def test_renders_suggested_actions(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.WARN, message="w")]
        report = build_report(checks=checks)
        report.suggested_actions = [
            SuggestedAction(action_id="clear_disk_cache", params={}, reason="Free space"),
        ]
        md = render_markdown(report)
        assert "## Suggested Actions" in md
        assert "clear_disk_cache" in md
        assert "Free space" in md

    def test_escapes_pipes_in_messages(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.OK, message="a|b")]
        report = build_report(checks=checks)
        md = render_markdown(report)
        assert "a\\|b" in md

    def test_overall_severity_icon(self) -> None:
        checks = [CheckResult(check_id="x", name="X", severity=Severity.CRITICAL, message="bad")]
        report = build_report(checks=checks)
        md = render_markdown(report)
        # CRITICAL uses red X
        assert "\u274c" in md
