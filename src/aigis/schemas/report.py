"""Health report schema."""

from datetime import datetime
from typing import Any

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
    collected_metrics: dict[str, list[dict[str, object]]] = {}  # collector_id -> list of signal dicts
    anomaly_explanation: str | None = None
    reasoning_trace: str | None = None
    detected_issues: list[dict[str, Any]] | None = None
    suggested_actions: list[SuggestedAction] | None = None
    manual_recommendations: list[dict[str, Any]] | None = None  # non-registry LLM steps: [{description, risk_level}]
    metadata: dict[str, str | int | float] = {}  # config_version, duration_ms, etc.
