"""Collector protocol and runner (Strategy pattern)."""

import shutil
from typing import TYPE_CHECKING, Protocol

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun

if TYPE_CHECKING:
    from aigis.runner import Runner


class CollectorProtocol(Protocol):
    """Protocol for data collectors. Each collector implements collect()."""

    @property
    def collector_id(self) -> str:
        """Unique identifier for this collector."""
        ...

    def collect(self, config: AppConfig, runner: "Runner") -> CollectorRun | list[CollectorRun]:
        """Collect signals. Returns one or more CollectorRun."""
        ...


def _check_required_commands(collector: CollectorProtocol) -> list[str]:
    """Return list of missing commands required by this collector."""
    required: list[str] = getattr(collector, "required_commands", [])
    return [cmd for cmd in required if shutil.which(cmd) is None]


def run_collectors(
    collectors: list[CollectorProtocol],
    config: AppConfig,
    runner: "Runner",
) -> list[CollectorRun]:
    """
    Run all collectors, never raising. Failed collectors produce CollectorRun
    with success=False and error_message set.
    """
    results: list[CollectorRun] = []
    for collector in collectors:
        if runner.is_local:
            missing = _check_required_commands(collector)
            if missing:
                results.append(
                    CollectorRun(
                        collector_id=collector.collector_id,
                        success=False,
                        error_message=f"Required command(s) not found: {', '.join(missing)}. "
                        f"Install them or disable the '{collector.collector_id}' collector.",
                    )
                )
                continue

        try:
            run = collector.collect(config, runner)
            if isinstance(run, list):
                results.extend(run)
            else:
                results.append(run)
        except Exception as exc:
            results.append(
                CollectorRun(
                    collector_id=collector.collector_id,
                    success=False,
                    error_message=str(exc),
                )
            )
    return results
