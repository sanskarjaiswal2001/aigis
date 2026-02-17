"""Network status collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, NetworkSignal


class NetworkCollector:
    """Collect network interface status."""

    collector_id = "network"

    def collect(self, config: AppConfig) -> CollectorRun:
        """Collect net_if_stats / net_if_addrs."""
        # TODO: psutil.net_if_stats(), net_if_addrs()
        # For now: stub
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=[NetworkSignal(interface="lo", up=True, addresses=["127.0.0.1"])],
        )
