"""Tests for collectors."""

from aigis.collectors import DiskCollector, LoadCollector, run_collectors
from aigis.config import AppConfig
from aigis.runner import LocalRunner


def test_run_collectors_returns_runs() -> None:
    """run_collectors returns list of CollectorRun."""
    config = AppConfig(target="local", targets={"local": {"host": ""}})
    runner = LocalRunner()
    collectors = [DiskCollector(), LoadCollector()]
    runs = run_collectors(collectors, config, runner)
    assert len(runs) >= 2
    assert all(r.collector_id in ("disk", "load") for r in runs)


def test_collector_protocol() -> None:
    """Collectors implement collector_id and collect()."""
    c = DiskCollector()
    assert c.collector_id == "disk"
    run = c.collect(AppConfig(target="local", targets={"local": {"host": ""}}), LocalRunner())
    assert run.success
    assert run.collector_id == "disk"
