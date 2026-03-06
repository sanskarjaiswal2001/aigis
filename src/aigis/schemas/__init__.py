"""Structured schemas for signals, checks, and reports."""

from aigis.schemas.actions import ActionId, ExecuteResult, SuggestedAction
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.report import HealthReport
from aigis.schemas.run_history import RunHistoryEntry, RunPhase
from aigis.schemas.signals import (
    CollectorRun,
    DiskSignal,
    DockerSignal,
    LoadSignal,
    NetworkSignal,
    ResticSignal,
)

__all__ = [
    "ActionId",
    "CheckResult",
    "CollectorRun",
    "DiskSignal",
    "DockerSignal",
    "ExecuteResult",
    "HealthReport",
    "LoadSignal",
    "NetworkSignal",
    "ResticSignal",
    "RunHistoryEntry",
    "RunPhase",
    "Severity",
    "SuggestedAction",
]
