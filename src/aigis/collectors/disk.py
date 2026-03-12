"""Disk usage collector."""

import re

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, DiskSignal


class DiskCollector:
    """Collect disk usage via psutil (local) or df (remote)."""

    collector_id = "disk"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Collect disk usage for configured mounts or auto-detect."""
        if runner.is_local:
            return self._collect_local(config)
        return self._collect_remote(config, runner)

    def _collect_local(self, config: AppConfig) -> CollectorRun:
        try:
            import psutil

            signals: list[DiskSignal] = []
            mounts = config.collectors.disk.mounts

            if mounts:
                for mp in mounts:
                    try:
                        usage = psutil.disk_usage(mp)
                        signals.append(
                            DiskSignal(
                                mount_point=mp,
                                used_pct=round(usage.percent, 1),
                                used_gb=round(usage.used / (1024**3), 2),
                                total_gb=round(usage.total / (1024**3), 2),
                                device=mp,
                            )
                        )
                    except (PermissionError, OSError):
                        pass
            else:
                for part in psutil.disk_partitions(all=False):
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        signals.append(
                            DiskSignal(
                                mount_point=part.mountpoint,
                                used_pct=round(usage.percent, 1),
                                used_gb=round(usage.used / (1024**3), 2),
                                total_gb=round(usage.total / (1024**3), 2),
                                device=part.device,
                            )
                        )
                    except (PermissionError, OSError):
                        pass

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
        # df -P: POSIX format, one line per filesystem; 1K blocks
        r = runner.run(["df", "-P", "-k"], timeout=15, login_shell=False)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr or f"df exited {r.returncode}",
            )
        signals: list[DiskSignal] = []
        mounts = config.collectors.disk.mounts
        for line in r.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            # Filesystem 1K-blocks Used Available Capacity Mounted
            device, total_k, used_k, avail_k, pcent_str, mount = (
                parts[0],
                int(parts[1]),
                int(parts[2]),
                int(parts[3]),
                parts[4],
                " ".join(parts[5:]),
            )
            if mounts and mount not in mounts:
                continue
            pct = float(pcent_str.rstrip("%")) if pcent_str.endswith("%") else 0.0
            total_gb = total_k / (1024 * 1024) if total_k else 0
            used_gb = used_k / (1024 * 1024) if used_k else 0
            signals.append(
                DiskSignal(
                    mount_point=mount,
                    used_pct=round(pct, 1),
                    used_gb=round(used_gb, 2),
                    total_gb=round(total_gb, 2),
                    device=device,
                )
            )
        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )
