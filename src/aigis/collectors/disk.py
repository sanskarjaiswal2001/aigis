"""Disk usage collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, DiskSignal


class DiskCollector:
    """Collect disk usage via psutil."""

    collector_id = "disk"

    def collect(self, config: AppConfig) -> CollectorRun:
        """Collect disk usage for configured mounts or auto-detect."""
        # TODO: psutil.disk_usage per mount
        # For now: stub
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=[DiskSignal(mount_point="/", used_pct=0.0, total_gb=0.0)],
        )
