"""Rule definitions (Specification pattern). Predicates over signals."""

from datetime import datetime, timezone

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.signals import CollectorRun, DiskSignal, DockerSignal, LoadSignal, NetworkSignal, ResticSignal

# Type alias for signal context (collector_id -> runs)
SignalContext = dict[str, list[CollectorRun]]


def _collector_error(runs: list[CollectorRun]) -> str:
    """Extract the first meaningful error_message from failed runs."""
    for run in runs:
        if not run.success and run.error_message:
            return run.error_message
    return "Collector failed or missing data"


def _is_repo_or_permission_error(stderr: str | None) -> bool:
    """True if stderr suggests repo unreachable or permission error."""
    if not stderr:
        return False
    low = stderr.lower()
    patterns = (
        "unable to open repo",
        "connection refused",
        "no such host",
        "wrong password",
        "permission denied",
        "repository not found",
        "access denied",
        "failed to open repository",
        "invalid repository",
    )
    return any(p in low for p in patterns)


def _evaluate_restic(ctx: SignalContext, config: AppConfig) -> CheckResult:
    """Restic: deterministic cascade (reachability, exit status, locks, freshness)."""
    runs = ctx.get("restic", [])
    if not runs:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.WARN,
            message="Collector failed or missing data",
            raw_signal_ref=None,
        )

    signal: ResticSignal | None = None
    for run in runs:
        for s in run.signals:
            if isinstance(s, ResticSignal):
                signal = s
                break
        if signal:
            break

    if not signal:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.WARN,
            message=_collector_error(runs),
            raw_signal_ref=None,
        )

    r = config.rules.restic

    # 2. Repo unreachable
    if not signal.repo_reachable:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.CRITICAL,
            message="Repository unreachable",
            value=signal.last_exit_code,
            raw_signal_ref=signal.repo_path or None,
        )

    # 3. Last exit code != 0 (snapshots succeeded but we captured a prior failure - actually no,
    #   if repo_reachable we already passed. So this is for when we have partial data. Actually
    #   in our collector, repo_reachable = (exit_code == 0) for snapshots. So we never get here with
    #   exit_code != 0 and repo_reachable. Skip this step - we only get signal with repo_reachable
    #   when snapshots succeeded. So steps 3 is for a different scenario. Let me re-read.
    #   Plan: "3. last_exit_code != 0: If stderr suggests repo/permission: CRITICAL. Else: WARN."
    #   So we could have a run where snapshots failed (repo_reachable=False) - we already handle that.
    #   Or we could have a run where snapshots succeeded but a subsequent probe (stats/locks) failed.
    #   In our collector, we only set last_exit_code from the snapshots run. So if repo_reachable,
    #   last_exit_code is 0. So step 3 is redundant when we have repo_reachable. I'll keep it for
    #   robustness in case we change the collector later.
    if signal.last_exit_code != 0:
        if _is_repo_or_permission_error(signal.last_stderr):
            return CheckResult(
                check_id="restic_backup",
                name="Restic backup",
                severity=Severity.CRITICAL,
                message="Repository or permission error",
                value=signal.last_exit_code,
                raw_signal_ref=signal.repo_path or None,
            )
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.WARN,
            message=f"Restic exited with code {signal.last_exit_code}",
            value=signal.last_exit_code,
            raw_signal_ref=signal.repo_path or None,
        )

    # 4. Stale lock
    if signal.stale_lock_detected:
        age_ok = signal.stale_lock_age_minutes is not None and signal.stale_lock_age_minutes < r.stale_lock_warn_minutes
        if not age_ok:  # age unknown or >= threshold
            return CheckResult(
                check_id="restic_backup",
                name="Restic backup",
                severity=Severity.WARN,
                message="Stale lock detected",
                value=signal.stale_lock_age_minutes,
                raw_signal_ref=signal.repo_path or None,
            )

    # 5. Backup freshness
    age_h = signal.last_snapshot_age_hours
    if age_h is None or age_h >= r.critical_hours:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.CRITICAL,
            message=f"Last backup missing or {age_h:.0f}h ago (critical: {r.critical_hours}h)" if age_h is not None else "No successful snapshot",
            value=age_h,
            raw_signal_ref=signal.repo_path or None,
        )
    if age_h >= r.warn_hours:
        return CheckResult(
            check_id="restic_backup",
            name="Restic backup",
            severity=Severity.WARN,
            message=f"Last backup {age_h:.0f}h ago (warn: {r.warn_hours}h)",
            value=round(age_h, 1),
            raw_signal_ref=signal.repo_path or None,
        )

    # 6. OK
    return CheckResult(
        check_id="restic_backup",
        name="Restic backup",
        severity=Severity.OK,
        message="OK",
        raw_signal_ref=signal.repo_path or None,
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
                message=_collector_error(runs) if runs else "Collector failed or missing data",
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
    if not results:
        results.append(
            CheckResult(
                check_id="disk_usage",
                name="Disk usage",
                severity=Severity.OK,
                message="OK",
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
            message=_collector_error(runs) if runs else "Collector failed or missing data",
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
                message=_collector_error(runs) if runs else "Collector failed or missing data",
            )
        ]

    configured_ifaces = set(config.collectors.network.interfaces)
    all_signals: list[NetworkSignal] = []
    for run in runs:
        for s in run.signals:
            if isinstance(s, NetworkSignal):
                all_signals.append(s)

    up_signals = [s for s in all_signals if s.up]
    down_signals = [s for s in all_signals if not s.up]

    results: list[CheckResult] = []

    if configured_ifaces:
        # User explicitly listed interfaces -- flag each downed one as CRITICAL
        for s in down_signals:
            if s.interface in configured_ifaces:
                results.append(
                    CheckResult(
                        check_id="network",
                        name="Network",
                        severity=Severity.CRITICAL,
                        message=f"Interface {s.interface} is down",
                        raw_signal_ref=s.interface,
                    )
                )
    elif not up_signals:
        # Auto-detect mode: CRITICAL only when *nothing* is up
        results.append(
            CheckResult(
                check_id="network",
                name="Network",
                severity=Severity.CRITICAL,
                message="No network interfaces are up",
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
                message=_collector_error(runs) if runs else "Collector failed or missing data",
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
