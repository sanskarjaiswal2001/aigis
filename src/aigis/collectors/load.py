"""System load collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, LoadSignal


class LoadCollector:
    """Collect system load average."""

    collector_id = "load"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Collect load average via psutil (local) or /proc/loadavg (remote)."""
        if runner.is_local:
            return self._collect_local(config)
        return self._collect_remote(config, runner)

    def _collect_local(self, config: AppConfig) -> CollectorRun:
        try:
            import psutil

            load_1, load_5, load_15 = psutil.getloadavg()
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[
                    LoadSignal(
                        load_1=round(load_1, 2),
                        load_5=round(load_5, 2),
                        load_15=round(load_15, 2),
                    )
                ],
            )
        except Exception as exc:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=str(exc),
            )

    def _collect_remote(self, config: AppConfig, runner) -> CollectorRun:
        r = runner.run(["cat", "/proc/loadavg"], timeout=config.collectors.restic.timeout_sec)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr or f"cat /proc/loadavg exited {r.returncode}",
            )
        parts = r.stdout.strip().split()
        if len(parts) < 3:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message="Could not parse loadavg",
            )
        try:
            load_1, load_5, load_15 = float(parts[0]), float(parts[1]), float(parts[2])
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[
                    LoadSignal(
                        load_1=round(load_1, 2),
                        load_5=round(load_5, 2),
                        load_15=round(load_15, 2),
                    )
                ],
            )
        except (ValueError, IndexError) as e:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=str(e),
            )
