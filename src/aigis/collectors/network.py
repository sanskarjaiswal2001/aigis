"""Network status collector."""

import socket

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, NetworkSignal

_IP_FAMILIES = {socket.AF_INET.value, socket.AF_INET6.value}


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
                    if getattr(a.family, "value", a.family) in _IP_FAMILIES
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
        # Use `ip addr show` (full format, no flags) — universally supported across all
        # iproute2 versions. The `-br` (brief) flag can fail on some configurations.
        r = runner.run(["ip", "addr", "show"], timeout=15, login_shell=False)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr.strip() or f"ip addr show exited {r.returncode}",
            )

        signals: list[NetworkSignal] = []
        ifaces = config.collectors.network.interfaces

        current_name: str | None = None
        current_up: bool = False
        current_addrs: list[str] = []

        def _flush() -> None:
            if current_name is None:
                return
            if ifaces and current_name not in ifaces:
                return
            signals.append(
                NetworkSignal(interface=current_name, up=current_up, addresses=list(current_addrs))
            )

        for line in r.stdout.splitlines():
            # Interface header line: "2: eth0: <FLAGS> ... state UP ..."
            if line and line[0].isdigit():
                _flush()
                parts = line.split()
                current_name = parts[1].rstrip(":") if len(parts) > 1 else None
                current_up = "state UP" in line or "state UNKNOWN" in line
                current_addrs = []
            # Address lines (indented with spaces/tabs)
            elif current_name and line.startswith(("    ", "\t")):
                stripped = line.strip()
                if stripped.startswith(("inet ", "inet6 ")):
                    addr_parts = stripped.split()
                    if len(addr_parts) >= 2:
                        current_addrs.append(addr_parts[1])

        _flush()

        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )
