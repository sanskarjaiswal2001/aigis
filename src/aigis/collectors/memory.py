"""Memory (RAM + swap) collector — psutil, local only."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, MemorySignal


class MemoryCollector:
    """Collect RAM and swap utilisation via psutil."""

    collector_id = "memory"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        if not runner.is_local:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message="Memory collector only supports local targets",
            )
        try:
            import psutil

            vm = psutil.virtual_memory()
            sw = psutil.swap_memory()

            signal = MemorySignal(
                used_pct=round(vm.percent, 1),
                used_gb=round(vm.used / (1024 ** 3), 2),
                total_gb=round(vm.total / (1024 ** 3), 2),
                available_gb=round(vm.available / (1024 ** 3), 2),
                swap_used_pct=round(sw.percent, 1),
                swap_used_gb=round(sw.used / (1024 ** 3), 2),
                swap_total_gb=round(sw.total / (1024 ** 3), 2),
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
