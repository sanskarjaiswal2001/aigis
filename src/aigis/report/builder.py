"""Report builder. Assembles HealthReport from CheckResults."""

import uuid
from datetime import datetime

from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.report import HealthReport
from aigis.schemas.signals import CollectorRun


def _overall_severity(checks: list[CheckResult]) -> Severity:
    """Compute max severity across checks."""
    order = {Severity.OK: 0, Severity.WARN: 1, Severity.CRITICAL: 2}
    max_sev = Severity.OK
    for c in checks:
        if order[c.severity] > order[max_sev]:
            max_sev = c.severity
    return max_sev


def _serialize_signals(collector_runs: list[CollectorRun]) -> dict[str, list[dict[str, object]]]:
    """Extract collected metrics from collector runs for report."""
    out: dict[str, list[dict[str, object]]] = {}
    for run in collector_runs:
        signals = []
        for s in run.signals:
            if hasattr(s, "model_dump"):
                signals.append(s.model_dump(mode="json"))
            elif isinstance(s, dict):
                signals.append(s)
            else:
                signals.append(str(s))
        out[run.collector_id] = signals
    return out


def build_report(
    checks: list[CheckResult],
    collector_runs: list[CollectorRun] | None = None,
    anomaly_explanation: str | None = None,
    reasoning_trace: str | None = None,
    detected_issues: list[dict] | None = None,
    manual_recommendations: list[dict] | None = None,
    metadata: dict[str, str | int | float] | None = None,
) -> HealthReport:
    """Build HealthReport from check results, collected metrics, and optional LLM explanation."""
    run_id = str(uuid.uuid4())[:8]
    overall = _overall_severity(checks)
    collected_metrics = _serialize_signals(collector_runs or [])
    return HealthReport(
        run_id=run_id,
        timestamp=datetime.now(),
        overall_severity=overall,
        checks=checks,
        collected_metrics=collected_metrics,
        anomaly_explanation=anomaly_explanation,
        reasoning_trace=reasoning_trace,
        detected_issues=detected_issues,
        manual_recommendations=manual_recommendations,
        metadata=metadata or {},
    )
