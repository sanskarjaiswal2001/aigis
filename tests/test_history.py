"""Tests for run history: load, build summaries, append."""

import json
from datetime import datetime
from pathlib import Path


from aigis.config import AppConfig, RunHistoryConfig
from aigis.history import (
    append_run_history,
    build_previous_run_summary,
    build_run_history_entry,
    build_trend_summary,
    load_run_history,
)
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.report import HealthReport
from aigis.schemas.run_history import RunHistoryEntry, RunPhase
from aigis.schemas.signals import CollectorRun


def _make_config(tmp_path: Path) -> AppConfig:
    """Create config pointing at a tmp history file."""
    return AppConfig(
        target="local",
        run_history=RunHistoryConfig(path=str(tmp_path / "history.jsonl"), last_n_runs=20),
    )


def _make_entry(
    run_id: str = "abc",
    severity: str = "OK",
    eval_details: dict | None = None,
    healing_details: dict | None = None,
    analysis_details: dict | None = None,
) -> RunHistoryEntry:
    """Build a minimal RunHistoryEntry."""
    phases = [
        RunPhase(category="collection", description="collect", steps=["Ran collector: disk (success)"], details={"disk": True}),
        RunPhase(
            category="evaluation",
            description="evaluate",
            steps=[f"Evaluated disk_usage -> {severity}: msg"],
            details=eval_details or {"disk_usage": severity},
        ),
        RunPhase(category="reporting", description="report", steps=[f"Overall severity: {severity}"]),
        RunPhase(
            category="analysis",
            description="analysis",
            details=analysis_details or {"suggested_count": 0},
        ),
    ]
    if healing_details:
        phases.append(RunPhase(category="healing", description="heal", details=healing_details))
    return RunHistoryEntry(
        run_id=run_id,
        timestamp=datetime.now().isoformat(),
        target="local",
        overall_severity=severity,
        phases=phases,
    )


class TestLoadRunHistory:
    """Tests for load_run_history."""

    def test_empty_when_no_file(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        assert load_run_history(config) == []

    def test_loads_entries(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        entry = _make_entry()
        path = Path(config.run_history.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.model_dump_json() + "\n")
        entries = load_run_history(config)
        assert len(entries) == 1
        assert entries[0].run_id == "abc"

    def test_respects_last_n(self, tmp_path: Path) -> None:
        config = AppConfig(
            target="local",
            run_history=RunHistoryConfig(path=str(tmp_path / "history.jsonl"), last_n_runs=2),
        )
        path = Path(config.run_history.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for i in range(5):
            e = _make_entry(run_id=f"run-{i}")
            lines.append(e.model_dump_json())
        path.write_text("\n".join(lines) + "\n")
        entries = load_run_history(config)
        assert len(entries) == 2
        assert entries[0].run_id == "run-3"
        assert entries[1].run_id == "run-4"

    def test_skips_invalid_lines(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        path = Path(config.run_history.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        valid = _make_entry(run_id="good")
        path.write_text("not-json\n" + valid.model_dump_json() + "\n\n")
        entries = load_run_history(config)
        assert len(entries) == 1
        assert entries[0].run_id == "good"


class TestBuildPreviousRunSummary:
    """Tests for build_previous_run_summary."""

    def test_none_for_empty(self) -> None:
        assert build_previous_run_summary([]) is None

    def test_returns_last_entry_summary(self) -> None:
        entry = _make_entry(run_id="run-1", severity="WARN")
        summary = build_previous_run_summary([entry])
        assert summary is not None
        assert summary["last_run_id"] == "run-1"
        assert summary["last_severity"] == "WARN"
        assert summary["last_target"] == "local"

    def test_detects_failed_checks(self) -> None:
        entry = _make_entry(
            severity="CRITICAL",
            eval_details={"disk_usage": "CRITICAL", "load": "OK"},
        )
        summary = build_previous_run_summary([entry])
        assert summary is not None
        assert "disk_usage:CRITICAL" in summary["last_failed_checks"]

    def test_detects_healing_actions(self) -> None:
        entry = _make_entry(
            severity="WARN",
            healing_details={"restart_container": True},
        )
        summary = build_previous_run_summary([entry])
        assert summary is not None
        assert len(summary["last_healing_actions"]) == 1
        assert summary["last_healing_actions"][0]["action_id"] == "restart_container"
        assert summary["any_wait_required"] is True

    def test_collector_failures(self) -> None:
        entry = _make_entry()
        # Override collection phase to have a failure
        entry.phases[0].details = {"disk": True, "restic": False}
        summary = build_previous_run_summary([entry])
        assert summary is not None
        assert "restic" in summary["last_collector_failures"]


class TestBuildTrendSummary:
    """Tests for build_trend_summary."""

    def test_none_for_single_entry(self) -> None:
        assert build_trend_summary([_make_entry()]) is None

    def test_none_for_empty(self) -> None:
        assert build_trend_summary([]) is None

    def test_detects_recurring_issues(self) -> None:
        entries = [
            _make_entry(run_id=f"r{i}", severity="WARN", eval_details={"disk_usage": "WARN"})
            for i in range(4)
        ]
        trend = build_trend_summary(entries)
        assert trend is not None
        assert trend["runs_analyzed"] == 4
        assert any("disk_usage" in r for r in trend["recurring_issues"])

    def test_detects_consecutive_failures(self) -> None:
        entries = [
            _make_entry(run_id="r0", severity="OK", eval_details={"disk_usage": "OK"}),
            _make_entry(run_id="r1", severity="CRITICAL", eval_details={"disk_usage": "CRITICAL"}),
            _make_entry(run_id="r2", severity="CRITICAL", eval_details={"disk_usage": "CRITICAL"}),
            _make_entry(run_id="r3", severity="CRITICAL", eval_details={"disk_usage": "CRITICAL"}),
        ]
        trend = build_trend_summary(entries)
        assert trend is not None
        assert any("disk_usage" in c for c in trend["consecutive_failures"])

    def test_none_when_no_issues(self) -> None:
        entries = [
            _make_entry(run_id=f"r{i}", severity="OK", eval_details={"disk_usage": "OK"})
            for i in range(5)
        ]
        assert build_trend_summary(entries) is None


class TestAppendRunHistory:
    """Tests for append_run_history."""

    def test_appends_entry(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        entry = _make_entry(run_id="appended")
        append_run_history(entry, config)
        path = Path(config.run_history.path)
        assert path.exists()
        lines = [l for l in path.read_text().strip().split("\n") if l]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["run_id"] == "appended"

    def test_appends_multiple(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        for i in range(3):
            append_run_history(_make_entry(run_id=f"r{i}"), config)
        path = Path(config.run_history.path)
        lines = [l for l in path.read_text().strip().split("\n") if l]
        assert len(lines) == 3


class TestBuildRunHistoryEntry:
    """Tests for build_run_history_entry."""

    def test_builds_entry_from_pipeline(self) -> None:
        report = HealthReport(
            run_id="test-run",
            overall_severity=Severity.WARN,
            checks=[
                CheckResult(check_id="disk_usage", name="Disk Usage", severity=Severity.WARN, message="85% used"),
            ],
        )
        collector_runs = [
            CollectorRun(collector_id="disk", success=True),
        ]
        checks = report.checks
        entry = build_run_history_entry(
            report=report,
            collector_runs=collector_runs,
            checks=checks,
            target="local",
            anomaly_explanation="Disk is filling up",
            suggested_action_count=1,
        )
        assert entry.run_id == "test-run"
        assert entry.overall_severity == "WARN"
        assert entry.target == "local"
        assert entry.anomaly_explanation == "Disk is filling up"
        categories = [p.category for p in entry.phases]
        assert "collection" in categories
        assert "evaluation" in categories
        assert "reporting" in categories
        assert "analysis" in categories

    def test_includes_healing_phase(self) -> None:
        report = HealthReport(run_id="heal-run", overall_severity=Severity.CRITICAL)
        entry = build_run_history_entry(
            report=report,
            collector_runs=[],
            checks=[],
            target="local",
            healing_results=[("restart_container", True), ("clear_disk_cache", False)],
        )
        healing = [p for p in entry.phases if p.category == "healing"]
        assert len(healing) == 1
        assert healing[0].details is not None
        assert healing[0].details["restart_container"] is True
        assert healing[0].details["clear_disk_cache"] is False
        assert healing[0].passes == "false"  # one action failed

    def test_no_healing_phase_when_empty(self) -> None:
        report = HealthReport(run_id="no-heal", overall_severity=Severity.OK)
        entry = build_run_history_entry(
            report=report, collector_runs=[], checks=[], target="local",
        )
        assert all(p.category != "healing" for p in entry.phases)
