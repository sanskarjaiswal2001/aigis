"""Network status collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, NetworkSignal


class NetworkCollector:
    """Collect network interface status."""

    collector_id = "network"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Collect net_if_stats (local) or ip link (remote)."""
        if runner.is_local:
            return self._collect_local(config)
        return self._collect_remote(config, runner)

    def _collect_local(self, config: AppConfig) -> CollectorRun:
        try:
            import psutil

            signals: list[NetworkSignal] = []
            ifaces = config.collectors.network.interfaces

            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for name, stat in stats.items():
                if ifaces and name not in ifaces:
                    continue
                addr_list = [
                    str(a.address)
                    for a in addrs.get(name, [])
                    if getattr(a.family, "value", a.family) in (2, 10)
                ]
                signals.append(
                    NetworkSignal(
                        interface=name,
                        up=stat.isup,
                        addresses=addr_list,
                    )
                )

            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=signals,
            )
        except Exception as exc:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=str(exc),
            )

    def _collect_remote(self, config: AppConfig, runner) -> CollectorRun:
        # ip -br addr: brief format, interface state and addresses
        r = runner.run(["ip", "-br", "addr", "show"], timeout=config.collectors.restic.timeout_sec)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr or f"ip exited {r.returncode}",
            )
        signals: list[NetworkSignal] = []
        ifaces = config.collectors.network.interfaces
        for line in r.stdout.strip().splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) < 2:
                continue
            name, state = parts[0], parts[1]
            if ifaces and name not in ifaces:
                continue
            addrs = parts[2].split() if len(parts) > 2 else []
            addr_list = [a for a in addrs if ":" not in a or a.startswith("inet")]
            signals.append(
                NetworkSignal(
                    interface=name,
                    up=state.upper() == "UP",
                    addresses=addr_list,
                )
            )
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )
