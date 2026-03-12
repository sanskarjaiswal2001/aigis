"""Run history schema: phase dicts and run envelope for agent continuity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RunPhase(BaseModel):
    """Single phase in a run (collection, evaluation, reporting, analysis, healing)."""

    model_config = ConfigDict(extra="forbid")

    category: str  # collection | evaluation | reporting | analysis | healing
    description: str
    steps: list[str] = Field(default_factory=list)
    passes: str = "true"  # "true" | "false" for JSON-friendly use
    details: dict[str, str | int | float | bool] | None = None


class RunHistoryEntry(BaseModel):
    """One run in history: envelope + phases for agent consumption."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    timestamp: str  # ISO format
    target: str
    overall_severity: str  # OK | WARN | CRITICAL
    phases: list[RunPhase] = Field(default_factory=list)
    anomaly_explanation: str | None = None
