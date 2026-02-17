"""Health report schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult, Severity


class HealthReport(BaseModel):
    """Full health report with overall severity."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    overall_severity: Severity = Severity.OK
    checks: list[CheckResult] = []
    anomaly_explanation: str | None = None
    suggested_actions: list[SuggestedAction] | None = None
    metadata: dict[str, str | int | float] = {}  # config_version, duration_ms, etc.
