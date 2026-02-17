"""Check result schemas."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Severity(str, Enum):
    """Health check severity level."""

    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class CheckResult(BaseModel):
    """Result of a single rule evaluation."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    name: str
    severity: Severity
    message: str
    value: str | float | int | None = None
    raw_signal_ref: str | None = None  # For audit trail
