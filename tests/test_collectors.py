"""Tests for collectors."""

from aigis.collectors import run_collectors
from aigis.config import AppConfig
from aigis.collectors import DiskCollector, LoadCollector


def test_run_collectors_returns_runs() -> None:
    """run_collectors returns list of CollectorRun."""
    config = AppConfig()
    collectors = [DiskCollector(), LoadCollector()]
    runs = run_collectors(collectors, config)
    assert len(runs) >= 2
    assert all(r.collector_id in ("disk", "load") for r in runs)


def test_collector_protocol() -> None:
    """Collectors implement collector_id and collect()."""
    c = DiskCollector()
    assert c.collector_id == "disk"
    run = c.collect(AppConfig())
    assert run.success
    assert run.collector_id == "disk"
