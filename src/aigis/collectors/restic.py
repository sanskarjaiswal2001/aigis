"""Restic backup status collector."""

import json
from datetime import datetime

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, ResticSignal


class ResticCollector:
    """Collect Restic backup status via restic snapshots."""

    collector_id = "restic"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Run restic snapshots and parse latest backup time."""
        repo = config.collectors.restic.repo_path or "/"
        timeout = config.collectors.restic.timeout_sec

        r = runner.run(["restic", "-r", repo, "snapshots", "--json"], timeout=timeout)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr[:500] if r.stderr else f"restic exited {r.returncode}",
            )

        try:
            data = json.loads(r.stdout)
            snapshots = data if isinstance(data, list) else data.get("data", data) if isinstance(data, dict) else []
            if not isinstance(snapshots, list):
                snapshots = []

            last_ts = None
            for s in snapshots:
                if isinstance(s, dict) and "time" in s:
                    try:
                        t = datetime.fromisoformat(str(s["time"]).replace("Z", "+00:00"))
                        if last_ts is None or t > last_ts:
                            last_ts = t
                    except (ValueError, TypeError):
                        pass

            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[
                    ResticSignal(
                        last_backup_ts=last_ts,
                        snapshot_count=len(snapshots),
                        repo_path=repo,
                    )
                ],
            )
        except json.JSONDecodeError as e:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=f"Invalid restic JSON: {e}",
            )
