"""System uptime collector."""

from datetime import datetime, timezone

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, UptimeSignal


class UptimeCollector:
    """Collect system uptime, boot time, and logged-in user count."""

    collector_id = "uptime"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        if runner.is_local:
            return self._collect_local()
        return self._collect_remote(runner)

    def _collect_local(self) -> CollectorRun:
        try:
            import psutil

            boot_ts = psutil.boot_time()
            boot_dt = datetime.fromtimestamp(boot_ts, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            uptime_sec = (now - boot_dt).total_seconds()

            usernames = {u.name for u in psutil.users()}

            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[
                    UptimeSignal(
                        boot_time=boot_dt,
                        uptime_seconds=uptime_sec,
                        uptime_human=_format_uptime(uptime_sec),
                        logged_in_users=len(usernames),
                    )
                ],
            )
        except Exception as exc:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=str(exc),
            )

    def _collect_remote(self, runner) -> CollectorRun:
        r = runner.run(["cat", "/proc/uptime"], timeout=10, login_shell=False)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr or f"exited {r.returncode}",
            )
        try:
            uptime_sec = float(r.stdout.strip().split()[0])
            now = datetime.now(tz=timezone.utc)
            boot_dt = datetime.fromtimestamp(
                now.timestamp() - uptime_sec, tz=timezone.utc
            )

            # Get logged-in user count
            user_r = runner.run(["who"], timeout=10, login_shell=False)
            user_count = 0
            if user_r.returncode == 0 and user_r.stdout.strip():
                usernames = {line.split()[0] for line in user_r.stdout.strip().splitlines() if line.strip()}
                user_count = len(usernames)

            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[
                    UptimeSignal(
                        boot_time=boot_dt,
                        uptime_seconds=uptime_sec,
                        uptime_human=_format_uptime(uptime_sec),
                        logged_in_users=user_count,
                    )
                ],
            )
        except Exception as exc:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=f"Failed to parse uptime: {exc}",
            )


def _format_uptime(seconds: float) -> str:
    """Format seconds into 'Xd Yh Zm' human-readable string."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
