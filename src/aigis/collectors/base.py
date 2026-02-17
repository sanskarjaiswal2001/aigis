"""Collector protocol and runner (Strategy pattern)."""

from typing import Protocol

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun


class CollectorProtocol(Protocol):
    """Protocol for data collectors. Each collector implements collect()."""

    @property
    def collector_id(self) -> str:
        """Unique identifier for this collector."""
        ...

    def collect(self, config: AppConfig) -> CollectorRun | list[CollectorRun]:
        """Collect signals. Returns one or more CollectorRun."""
        ...


def run_collectors(
    collectors: list[CollectorProtocol],
    config: AppConfig,
) -> list[CollectorRun]:
    """
    Run all collectors, never raising. Failed collectors produce CollectorRun
    with success=False and error_message set.
    """
    results: list[CollectorRun] = []
    for collector in collectors:
        try:
            run = collector.collect(config)
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
