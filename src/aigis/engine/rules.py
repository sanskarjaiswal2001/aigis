"""Rule definitions (Specification pattern). Predicates over signals."""

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.signals import CollectorRun

# Type alias for signal context (collector_id -> signals)
SignalContext = dict[str, list[CollectorRun]]


def _evaluate_restic(ctx: SignalContext, config: AppConfig) -> CheckResult:
    """Restic: last backup age thresholds."""
    runs = ctx.get("restic", [])
    if not runs or not runs[0].success:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.WARN,
            message="Collector failed or missing data",
        )
    # TODO: parse ResticSignal, compute age, compare to config.rules.restic
    return CheckResult(
        check_id="restic_backup",
        name="Restic backup",
        severity=Severity.OK,
        message="OK",
    )


def _evaluate_disk(ctx: SignalContext, config: AppConfig) -> list[CheckResult]:
    """Disk: used_pct thresholds per mount."""
    runs = ctx.get("disk", [])
    if not runs or not runs[0].success:
        return [
            CheckResult(
                check_id="disk_usage",
                name="Disk usage",
                severity=Severity.WARN,
                message="Collector failed or missing data",
            )
        ]
    # TODO: iterate DiskSignal, compare to config.rules.disk
    return []


def _evaluate_load(ctx: SignalContext, config: AppConfig) -> CheckResult:
    """Load: load_1 / cpu_count thresholds."""
    runs = ctx.get("load", [])
    if not runs or not runs[0].success:
        return CheckResult(
            check_id="system_load",
            name="System load",
            severity=Severity.WARN,
            message="Collector failed or missing data",
        )
    # TODO: parse LoadSignal, get cpu_count, compare to config.rules.load
    return CheckResult(
        check_id="system_load",
        name="System load",
        severity=Severity.OK,
        message="OK",
    )


def _evaluate_network(ctx: SignalContext, config: AppConfig) -> list[CheckResult]:
    """Network: interface up/down."""
    runs = ctx.get("network", [])
    if not runs or not runs[0].success:
        return [
            CheckResult(
                check_id="network",
                name="Network",
                severity=Severity.WARN,
                message="Collector failed or missing data",
            )
        ]
    # TODO: iterate NetworkSignal
    return []


def _evaluate_docker(ctx: SignalContext, config: AppConfig) -> list[CheckResult]:
    """Docker: container state and health."""
    runs = ctx.get("docker", [])
    if not runs or not runs[0].success:
        return [
            CheckResult(
                check_id="docker",
                name="Docker",
                severity=Severity.WARN,
                message="Collector failed or missing data",
            )
        ]
    # TODO: iterate DockerSignal
    return []


def evaluate_all_rules(
    collector_runs: list[CollectorRun],
    config: AppConfig,
) -> list[CheckResult]:
    """Run all rules over collector runs. Returns flat list of CheckResults."""
    ctx: SignalContext = {}
    for run in collector_runs:
        ctx.setdefault(run.collector_id, []).append(run)

    results: list[CheckResult] = []
    results.append(_evaluate_restic(ctx, config))
    results.extend(_evaluate_disk(ctx, config))
    results.append(_evaluate_load(ctx, config))
    results.extend(_evaluate_network(ctx, config))
    results.extend(_evaluate_docker(ctx, config))
    return results
