"""System load collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, LoadSignal


class LoadCollector:
    """Collect system load average."""

    collector_id = "load"

    def collect(self, config: AppConfig) -> CollectorRun:
        """Collect load average via psutil.getloadavg()."""
        # TODO: psutil.getloadavg()
        # For now: stub
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=[LoadSignal(load_1=0.0, load_5=0.0, load_15=0.0)],
        )
