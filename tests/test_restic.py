"""Tests for Restic collector and rules."""

from aigis.collectors import ResticCollector, run_collectors
from aigis.config import AppConfig
from aigis.engine import run_rules
from aigis.schemas.checks import Severity
from aigis.schemas.signals import CollectorRun, ResticSignal
from aigis.runner import RunResult


class MockRunner:
    """Runner that returns predefined results for restic commands."""

    is_local = True

    def __init__(self, snapshots_result: RunResult, stats_result: RunResult | None = None, locks_result: RunResult | None = None):
        self.snapshots_result = snapshots_result
        self.stats_result = stats_result or RunResult(stdout="", stderr="", returncode=0)
        self.locks_result = locks_result or RunResult(stdout="", stderr="", returncode=0)

    def run(self, cmd: list[str], timeout: int = 30) -> RunResult:
        if "snapshots" in cmd:
            return self.snapshots_result
        if "stats" in cmd:
            return self.stats_result
        if "locks" in cmd:
            return self.locks_result
        return RunResult(stdout="", stderr="", returncode=-1)


def test_restic_collector_success() -> None:
    """ResticCollector returns ResticSignal with full structured output on success."""
    snapshot_json = '[{"time": "2025-02-17T12:00:00Z"}]'
    stats_out = "Total size: 1073741824 B"  # 1 GB
    runner = MockRunner(
        snapshots_result=RunResult(stdout=snapshot_json, stderr="", returncode=0),
        stats_result=RunResult(stdout=stats_out, stderr="", returncode=0),
        locks_result=RunResult(stdout="", stderr="", returncode=0),
    )
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    collectors = [ResticCollector()]
    runs = run_collectors(collectors, config, runner)
    assert len(runs) == 1
    assert runs[0].success
    assert len(runs[0].signals) == 1
    sig = runs[0].signals[0]
    assert isinstance(sig, ResticSignal)
    assert sig.repo_reachable is True
    assert sig.last_exit_code == 0
    assert sig.snapshot_count == 1
    assert sig.last_snapshot_age_hours is not None
    assert sig.stale_lock_detected is False


def test_restic_collector_failure() -> None:
    """ResticCollector returns ResticSignal with failure info when snapshots fail."""
    runner = MockRunner(
        snapshots_result=RunResult(stdout="", stderr="unable to open repo", returncode=1),
    )
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    collectors = [ResticCollector()]
    runs = run_collectors(collectors, config, runner)
    assert len(runs) == 1
    assert not runs[0].success
    assert len(runs[0].signals) == 1
    sig = runs[0].signals[0]
    assert isinstance(sig, ResticSignal)
    assert sig.repo_reachable is False
    assert sig.last_exit_code == 1
    assert sig.last_stderr == "unable to open repo"


def test_restic_collector_stale_lock() -> None:
    """ResticCollector sets stale_lock_detected when locks exist."""
    snapshot_json = '[{"time": "2025-02-17T12:00:00Z"}]'
    runner = MockRunner(
        snapshots_result=RunResult(stdout=snapshot_json, stderr="", returncode=0),
        locks_result=RunResult(stdout="abc123def456\n", stderr="", returncode=0),
    )
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    collectors = [ResticCollector()]
    runs = run_collectors(collectors, config, runner)
    assert len(runs) == 1
    sig = runs[0].signals[0]
    assert isinstance(sig, ResticSignal)
    assert sig.stale_lock_detected is True


def test_restic_rules_unreachable() -> None:
    """Rule engine returns CRITICAL when repo unreachable."""
    signal = ResticSignal(
        repo_reachable=False,
        last_exit_code=1,
        repo_path="/repo",
    )
    runs = [CollectorRun(collector_id="restic", success=False, signals=[signal], error_message="unable to open repo")]
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    checks = run_rules(runs, config)
    restic_checks = [c for c in checks if c.check_id == "restic_backup"]
    assert len(restic_checks) == 1
    assert restic_checks[0].severity == Severity.CRITICAL


def test_restic_rules_stale_lock() -> None:
    """Rule engine returns WARN when stale lock detected and age exceeds threshold."""
    signal = ResticSignal(
        repo_reachable=True,
        last_exit_code=0,
        last_snapshot_age_hours=1.0,
        stale_lock_detected=True,
        stale_lock_age_minutes=120.0,  # 2 hours
        snapshot_count=5,
        repo_path="/repo",
    )
    runs = [CollectorRun(collector_id="restic", success=True, signals=[signal])]
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    checks = run_rules(runs, config)
    restic_checks = [c for c in checks if c.check_id == "restic_backup"]
    assert len(restic_checks) == 1
    assert restic_checks[0].severity == Severity.WARN
    assert "Stale lock" in restic_checks[0].message


def test_restic_rules_freshness_critical() -> None:
    """Rule engine returns CRITICAL when backup age exceeds critical threshold."""
    signal = ResticSignal(
        repo_reachable=True,
        last_exit_code=0,
        last_snapshot_age_hours=72.0,  # 3 days
        stale_lock_detected=False,
        snapshot_count=5,
        repo_path="/repo",
    )
    runs = [CollectorRun(collector_id="restic", success=True, signals=[signal])]
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    checks = run_rules(runs, config)
    restic_checks = [c for c in checks if c.check_id == "restic_backup"]
    assert len(restic_checks) == 1
    assert restic_checks[0].severity == Severity.CRITICAL


def test_restic_rules_no_snapshot() -> None:
    """Rule engine returns CRITICAL when repo reachable but no snapshot exists."""
    signal = ResticSignal(
        repo_reachable=True,
        last_exit_code=0,
        last_snapshot_age_hours=None,  # no snapshots
        stale_lock_detected=False,
        snapshot_count=0,
        repo_path="/repo",
    )
    runs = [CollectorRun(collector_id="restic", success=True, signals=[signal])]
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    checks = run_rules(runs, config)
    restic_checks = [c for c in checks if c.check_id == "restic_backup"]
    assert len(restic_checks) == 1
    assert restic_checks[0].severity == Severity.CRITICAL
    assert "No successful snapshot" in restic_checks[0].message or "missing" in restic_checks[0].message.lower()


def test_restic_rules_ok() -> None:
    """Rule engine returns OK when all checks pass."""
    signal = ResticSignal(
        repo_reachable=True,
        last_exit_code=0,
        last_snapshot_age_hours=12.0,
        stale_lock_detected=False,
        snapshot_count=10,
        repo_path="/repo",
    )
    runs = [CollectorRun(collector_id="restic", success=True, signals=[signal])]
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    checks = run_rules(runs, config)
    restic_checks = [c for c in checks if c.check_id == "restic_backup"]
    assert len(restic_checks) == 1
    assert restic_checks[0].severity == Severity.OK
