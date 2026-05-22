"""Windows Services watchdog collector — psutil, local Windows only."""

import platform

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, WindowsServiceSignal

_IS_WINDOWS = platform.system() == "Windows"


class WindowsServicesCollector:
    """Check configured Windows services are running via psutil."""

    collector_id = "windows_services"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        services = config.collectors.windows_services.services

        if not services:
            # Nothing configured — skip silently (return success with no signals)
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[],
            )

        if not runner.is_local:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message="Windows Services collector only supports local targets",
            )

        if not _IS_WINDOWS:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message="Windows Services collector is only supported on Windows",
            )

        try:
            import psutil

            signals: list[WindowsServiceSignal] = []
            for name in services:
                try:
                    svc = psutil.win_service_get(name)
                    info = svc.as_dict()
                    signals.append(
                        WindowsServiceSignal(
                            name=name,
                            display_name=info.get("display_name") or name,
                            status=info.get("status", "unknown"),
                            start_type=info.get("start_type", "unknown"),
                        )
                    )
                except psutil.NoSuchProcess:
                    signals.append(
                        WindowsServiceSignal(
                            name=name,
                            display_name=name,
                            status="not_found",
                            start_type="unknown",
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
