"""Docker container health collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, DockerSignal


class DockerCollector:
    """Collect Docker container status via docker ps or SDK."""

    collector_id = "docker"

    def collect(self, config: AppConfig) -> CollectorRun:
        """Collect docker ps output."""
        # TODO: docker SDK or subprocess docker ps
        # For now: stub
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=[],
        )
