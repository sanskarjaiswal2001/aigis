"""Report builder. Assembles HealthReport from CheckResults."""

import uuid
from datetime import datetime

from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.report import HealthReport


def _overall_severity(checks: list[CheckResult]) -> Severity:
    """Compute max severity across checks."""
    order = {Severity.OK: 0, Severity.WARN: 1, Severity.CRITICAL: 2}
    max_sev = Severity.OK
    for c in checks:
        if order[c.severity] > order[max_sev]:
            max_sev = c.severity
    return max_sev


def build_report(
    checks: list[CheckResult],
    anomaly_explanation: str | None = None,
    metadata: dict[str, str | int | float] | None = None,
) -> HealthReport:
    """Build HealthReport from check results and optional LLM explanation."""
    run_id = str(uuid.uuid4())[:8]
    overall = _overall_severity(checks)
    return HealthReport(
        run_id=run_id,
        timestamp=datetime.now(),
        overall_severity=overall,
        checks=checks,
        anomaly_explanation=anomaly_explanation,
        metadata=metadata or {},
    )
