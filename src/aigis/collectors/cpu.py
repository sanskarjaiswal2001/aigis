"""CPU utilisation collector — psutil, local only."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, CpuSignal


class CpuCollector:
    """Collect CPU utilisation and top N processes via psutil."""

    collector_id = "cpu"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        if not runner.is_local:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message="CPU collector only supports local targets",
            )
        try:
            import psutil

            # Measure over a 1-second interval for accuracy.
            used_pct = psutil.cpu_percent(interval=1)
            core_count = psutil.cpu_count(logical=True) or 1

            top_n = config.collectors.cpu.top_n_processes

            # Warm up cpu_percent for each process (first call returns 0.0).
            procs = []
            for p in psutil.process_iter(["name", "pid", "cpu_percent"]):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort descending and take top N (exclude system idle process on Windows)
            top = sorted(
                [p for p in procs if p.get("cpu_percent", 0) > 0],
                key=lambda p: p.get("cpu_percent", 0),
                reverse=True,
            )[:top_n]

            signal = CpuSignal(
                used_pct=round(used_pct, 1),
                core_count=core_count,
                top_processes=[
                    {"name": p["name"], "pid": p["pid"], "cpu_pct": round(p["cpu_percent"], 1)}
                    for p in top
                ],
            )
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[signal],
            )
        except Exception as exc:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=str(exc),
            )
