"""Run history: load, build entry, append. Enables continuity (previous-run context) for new runs."""

import json
from pathlib import Path
from typing import Any

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult
from aigis.schemas.report import HealthReport
from aigis.schemas.run_history import RunHistoryEntry, RunPhase
from aigis.schemas.signals import CollectorRun

# Actions that require waiting (e.g. restart, backup) before re-checking; next run should not repeat same fix.
WAIT_REQUIRED_ACTION_IDS = frozenset({"restart_container", "run_restic_backup"})


def _resolve_history_path(config: AppConfig) -> Path:
    path = Path(config.run_history.path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_run_history(config: AppConfig) -> list[RunHistoryEntry]:
    """Load last N run entries from JSONL (most recent last). Returns empty list if file missing or invalid."""
    path = _resolve_history_path(config)
    if not path.exists():
        return []
    entries: list[RunHistoryEntry] = []
    n = config.run_history.last_n_runs
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(RunHistoryEntry.model_validate(data))
                except Exception:
                    continue
        # Keep only last N
        return entries[-n:] if len(entries) > n else entries
    except Exception:
        return []


def build_previous_run_summary(entries: list[RunHistoryEntry]) -> dict[str, Any] | None:
    """
    Build a small summary from the most recent run for LLM/continuity.
    Keys: last_run_id, last_timestamp, last_target, last_severity, last_failed_checks,
    last_failed_check_messages, last_collector_failures, last_suggested_action_count,
    last_healing_actions, any_wait_required.
    """
    if not entries:
        return None
    last = entries[-1]
    failed_checks: list[str] = []
    failed_check_messages: dict[str, str] = {}
    for p in last.phases:
        if p.category == "evaluation":
            if p.details:
                for check_id, sev in p.details.items():
                    if isinstance(sev, str) and sev in ("WARN", "CRITICAL"):
                        failed_checks.append(f"{check_id}:{sev}")
            # Parse steps "Evaluated check_id -> SEV: message" for messages
            for step in p.steps:
                if " → " in step and ": " in step:
                    try:
                        left, rest = step.split(" → ", 1)
                        if left.strip().startswith("Evaluated "):
                            check_id = left.replace("Evaluated", "").strip()
                            sev_msg = rest.split(": ", 1)
                            if len(sev_msg) == 2 and sev_msg[0] in ("WARN", "CRITICAL"):
                                failed_check_messages[check_id] = sev_msg[1].strip()
                    except Exception:
                        pass
    collector_failures: list[str] = []
    for p in last.phases:
        if p.category == "collection" and p.details:
            for cid, ok in p.details.items():
                if isinstance(ok, bool) and not ok:
                    collector_failures.append(cid)
    suggested_count = 0
    for p in last.phases:
        if p.category == "analysis" and p.details:
            suggested_count = int(p.details.get("suggested_count", 0) or 0)
            break
    healing_actions: list[dict[str, Any]] = []
    any_wait_required = False
    for p in last.phases:
        if p.category == "healing" and p.details:
            for action_id, success in p.details.items():
                if isinstance(success, bool):
                    healing_actions.append({"action_id": action_id, "success": success})
                    if action_id in WAIT_REQUIRED_ACTION_IDS:
                        any_wait_required = True
    return {
        "last_run_id": last.run_id,
        "last_timestamp": last.timestamp,
        "last_target": last.target,
        "last_severity": last.overall_severity,
        "last_failed_checks": failed_checks,
        "last_failed_check_messages": failed_check_messages,
        "last_collector_failures": collector_failures,
        "last_suggested_action_count": suggested_count,
        "last_healing_actions": healing_actions,
        "any_wait_required": any_wait_required,
    }


def build_run_history_entry(
    report: HealthReport,
    collector_runs: list[CollectorRun],
    checks: list[CheckResult],
    target: str,
    anomaly_explanation: str | None = None,
    suggested_action_count: int = 0,
    healing_results: list[tuple[str, bool]] | None = None,
) -> RunHistoryEntry:
    """
    Build one RunHistoryEntry from pipeline outputs.
    healing_results: optional list of (action_id, success) for executed actions.
    """
    phases: list[RunPhase] = []

    # Collection
    steps = []
    details: dict[str, bool] = {}
    for run in collector_runs:
        steps.append(
            f"Ran collector: {run.collector_id} ({'success' if run.success else 'failed'}"
            + (f": {run.error_message}" if run.error_message else "")
            + ")"
        )
        details[run.collector_id] = run.success
    collection_passes = all(r.success for r in collector_runs) if collector_runs else True
    phases.append(
        RunPhase(
            category="collection",
            description="Gather metrics from enabled collectors",
            steps=steps,
            passes="true" if collection_passes else "false",
            details=details,
        )
    )

    # Evaluation
    eval_steps = []
    eval_details: dict[str, str] = {}
    for c in checks:
        eval_steps.append(f"Evaluated {c.check_id} → {c.severity.value}: {c.message}")
        eval_details[c.check_id] = c.severity.value
    has_critical = any(c.severity.value == "CRITICAL" for c in checks)
    phases.append(
        RunPhase(
            category="evaluation",
            description="Evaluate rules against collected signals",
            steps=eval_steps,
            passes="false" if has_critical else "true",
            details=eval_details,
        )
    )

    # Reporting
    phases.append(
        RunPhase(
            category="reporting",
            description="Build health report and overall severity",
            steps=[
                f"Built report run_id={report.run_id}",
                f"Overall severity: {report.overall_severity.value}",
            ],
            passes="true",
        )
    )

    # Analysis
    phases.append(
        RunPhase(
            category="analysis",
            description="LLM explanation and suggested fixes",
            steps=[
                "LLM analysis: anomaly_explanation present" if anomaly_explanation else "LLM analysis: skipped or none",
                f"Suggested {suggested_action_count} actions",
            ],
            passes="true",
            details={"suggested_count": suggested_action_count},
        )
    )

    # Healing (if any)
    if healing_results:
        steps = [f"Executed {aid} ({'success' if ok else 'failed'})" for aid, ok in healing_results]
        details_heal = {aid: ok for aid, ok in healing_results}
        all_ok = all(ok for _, ok in healing_results)
        phases.append(
            RunPhase(
                category="healing",
                description="Apply suggested actions after human approval",
                steps=steps,
                passes="true" if all_ok else "false",
                details=details_heal,
            )
        )

    return RunHistoryEntry(
        run_id=report.run_id,
        timestamp=report.timestamp.isoformat(),
        target=target,
        overall_severity=report.overall_severity.value,
        phases=phases,
    )


def append_run_history(entry: RunHistoryEntry, config: AppConfig) -> None:
    """Append one run entry as a single JSON line to the history file."""
    path = _resolve_history_path(config)
    with path.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")
