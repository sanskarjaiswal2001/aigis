"""Restic backup status collector."""

from datetime import datetime

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, ResticSignal


class ResticCollector:
    """Collect Restic backup status via restic snapshots."""

    collector_id = "restic"

    def collect(self, config: AppConfig) -> CollectorRun:
        """Run restic snapshots and parse latest backup time."""
        # TODO: subprocess.run(["restic", "snapshots"], timeout=config.collectors.restic.timeout_sec)
        # For now: stub returning empty signal
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=[ResticSignal(repo_path=config.collectors.restic.repo_path or "/")],
        )
