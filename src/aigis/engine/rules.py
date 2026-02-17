"""Rule definitions (Specification pattern). Predicates over signals."""

from datetime import datetime, timezone

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.signals import CollectorRun, DiskSignal, DockerSignal, LoadSignal, NetworkSignal

# Type alias for signal context (collector_id -> runs)
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
    for run in runs:
        for s in run.signals:
            if hasattr(s, "last_backup_ts") and s.last_backup_ts:
                age_h = (datetime.now(timezone.utc) - s.last_backup_ts).total_seconds() / 3600
                if age_h >= config.rules.restic.critical_hours:
                    return CheckResult(
                        check_id="restic_backup",
                        name="Restic backup",
                        severity=Severity.CRITICAL,
                        message=f"Last backup {age_h:.0f}h ago (critical: {config.rules.restic.critical_hours}h)",
                        value=round(age_h, 1),
                    )
                if age_h >= config.rules.restic.warn_hours:
                    return CheckResult(
                        check_id="restic_backup",
                        name="Restic backup",
                        severity=Severity.WARN,
                        message=f"Last backup {age_h:.0f}h ago (warn: {config.rules.restic.warn_hours}h)",
                        value=round(age_h, 1),
                    )
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
    results: list[CheckResult] = []
    for run in runs:
        for s in run.signals:
            if isinstance(s, DiskSignal):
                pct = s.used_pct
                mp = s.mount_point or "?"
                if pct >= config.rules.disk.critical_pct:
                    results.append(
                        CheckResult(
                            check_id="disk_usage",
                            name="Disk usage",
                            severity=Severity.CRITICAL,
                            message=f"{mp}: {pct}% used (critical: {config.rules.disk.critical_pct}%)",
                            value=pct,
                            raw_signal_ref=mp,
                        )
                    )
                elif pct >= config.rules.disk.warn_pct:
                    results.append(
                        CheckResult(
                            check_id="disk_usage",
                            name="Disk usage",
                            severity=Severity.WARN,
                            message=f"{mp}: {pct}% used (warn: {config.rules.disk.warn_pct}%)",
                            value=pct,
                            raw_signal_ref=mp,
                        )
                    )
    return results


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
    try:
        import psutil

        cpu_count = psutil.cpu_count() or 1
    except Exception:
        cpu_count = 1
    for run in runs:
        for s in run.signals:
            if isinstance(s, LoadSignal):
                per_cpu = s.load_1 / cpu_count if cpu_count else s.load_1
                if per_cpu >= config.rules.load.critical_per_cpu:
                    return CheckResult(
                        check_id="system_load",
                        name="System load",
                        severity=Severity.CRITICAL,
                        message=f"load_1/cpu={per_cpu:.1f} (critical: {config.rules.load.critical_per_cpu})",
                        value=round(per_cpu, 2),
                    )
                if per_cpu >= config.rules.load.warn_per_cpu:
                    return CheckResult(
                        check_id="system_load",
                        name="System load",
                        severity=Severity.WARN,
                        message=f"load_1/cpu={per_cpu:.1f} (warn: {config.rules.load.warn_per_cpu})",
                        value=round(per_cpu, 2),
                    )
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
    results: list[CheckResult] = []
    for run in runs:
        for s in run.signals:
            if isinstance(s, NetworkSignal) and not s.up:
                results.append(
                    CheckResult(
                        check_id="network",
                        name="Network",
                        severity=Severity.CRITICAL,
                        message=f"Interface {s.interface} is down",
                        raw_signal_ref=s.interface,
                    )
                )
    return results


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
    results: list[CheckResult] = []
    for run in runs:
        for s in run.signals:
            if isinstance(s, DockerSignal):
                if s.state != "running":
                    results.append(
                        CheckResult(
                            check_id="docker",
                            name="Docker",
                            severity=Severity.WARN,
                            message=f"Container {s.name} not running: {s.state}",
                            value=s.state,
                            raw_signal_ref=s.name,
                        )
                    )
                elif s.health and "unhealthy" in s.health.lower():
                    results.append(
                        CheckResult(
                            check_id="docker",
                            name="Docker",
                            severity=Severity.WARN,
                            message=f"Container {s.name} unhealthy: {s.health}",
                            value=s.health,
                            raw_signal_ref=s.name,
                        )
                    )
    return results


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
