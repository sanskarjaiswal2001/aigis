"""Restic backup status collector (MVP: freshness, exit status, reachability, locks)."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, ResticSignal


def _parse_size_bytes(text: str) -> float | None:
    """Parse repo size from restic stats output. Returns bytes or None."""
    # restic stats outputs "Total size: 1.234 GiB" or "total_size": 1234567 in JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            size = data.get("total_size") or data.get("totalSize") or data.get("size")
            if size is not None:
                return float(size)
    except json.JSONDecodeError:
        pass
    # Fallback: parse "Total size: X B/KiB/MiB/GiB" from text
    m = re.search(r"total\s+size[:\s]+(\d+(?:\.\d+)?)\s*([KMGT]?i?B)", text, re.I)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "B").upper()
        if unit in ("B", ""):
            return val
        if unit.startswith("KI"):
            return val * 1024
        if unit.startswith("MI"):
            return val * 1024**2
        if unit.startswith("GI"):
            return val * 1024**3
        if unit.startswith("TI"):
            return val * 1024**4
    return None


def _parse_lock_age(text: str) -> float | None:
    """Parse lock age from restic list locks output if possible. Returns minutes or None."""
    # Standard restic list locks outputs lock IDs only (hex strings). No age in default output.
    # If JSON format exists, look for "time" field.
    try:
        lines = text.strip().splitlines()
        for line in lines:
            data = json.loads(line)
            if isinstance(data, dict) and "time" in data:
                t = datetime.fromisoformat(str(data["time"]).replace("Z", "+00:00"))
                age_s = (datetime.now(timezone.utc) - t).total_seconds()
                return age_s / 60.0
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def _is_restic_repo(path: Path) -> bool:
    """Check if a directory has the structure of a restic repository."""
    try:
        return (
            (path / "config").is_file()
            and (path / "data").is_dir()
            and (path / "keys").is_dir()
        )
    except (PermissionError, OSError):
        return False


def _discover_repo() -> str | None:
    """Try to find an existing restic repo: env var, then filesystem scan."""
    env_repo = os.environ.get("RESTIC_REPOSITORY")
    if env_repo:
        return env_repo

    home = Path.home()
    search_roots = [
        home,
        home / "backups",
        home / "backup",
        home / "restic",
        home / "restic-repo",
        home / ".restic",
        Path("/srv/restic"),
        Path("/var/backups"),
    ]

    for root in search_roots:
        if not root.is_dir():
            continue
        if _is_restic_repo(root):
            return str(root)
        try:
            for child in root.iterdir():
                if child.is_dir() and _is_restic_repo(child):
                    return str(child)
        except (PermissionError, OSError):
            continue

    return None


class ResticCollector:
    """Collect Restic backup status via snapshots, stats, and locks probes."""

    collector_id = "restic"
    required_commands = ["restic"]

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Run restic probes and build structured ResticSignal."""
        repo: str | None = config.collectors.restic.repo_path or None

        if not repo and runner.is_local:
            repo = _discover_repo()
            if not repo:
                return CollectorRun(
                    collector_id=self.collector_id,
                    success=False,
                    error_message="No restic repo configured and none found. "
                    "Set collectors.restic.repo_path in config or RESTIC_REPOSITORY env var.",
                )

        # For remote runners with no repo_path: omit -r and let the remote host's
        # RESTIC_REPOSITORY env var (from ~/.profile) supply the repo.
        timeout = config.collectors.restic.timeout_sec
        expected_hours = config.collectors.restic.expected_interval_hours

        def _restic_cmd(subcmd: list[str]) -> list[str]:
            return ["restic", "-r", repo, *subcmd] if repo else ["restic", *subcmd]

        # Probe 1: snapshots (primary - determines reachability)
        r = runner.run(_restic_cmd(["snapshots", "--json"]), timeout=timeout)
        exit_code = r.returncode
        stderr = (r.stderr or "")[:500]

        last_ts = None
        snapshot_count = 0
        repo_reachable = exit_code == 0

        if exit_code == 0:
            try:
                data = json.loads(r.stdout)
                snapshots = data if isinstance(data, list) else data.get("data", data) if isinstance(data, dict) else []
                if not isinstance(snapshots, list):
                    snapshots = []
                snapshot_count = len(snapshots)
                for s in snapshots:
                    if isinstance(s, dict) and "time" in s:
                        try:
                            t = datetime.fromisoformat(str(s["time"]).replace("Z", "+00:00"))
                            if last_ts is None or t > last_ts:
                                last_ts = t
                        except (ValueError, TypeError):
                            pass
            except json.JSONDecodeError:
                pass

        # Compute last_snapshot_age_hours
        last_snapshot_age_hours = None
        if last_ts:
            ts_utc = last_ts if last_ts.tzinfo else last_ts.replace(tzinfo=timezone.utc)
            last_snapshot_age_hours = (datetime.now(timezone.utc) - ts_utc).total_seconds() / 3600

        # Probes 2 & 3: stats and locks (only if repo reachable)
        repo_size_gb = None
        stale_lock_detected = False
        stale_lock_age_minutes = None

        if repo_reachable:
            r_stats = runner.run(_restic_cmd(["stats", "--mode", "raw-data"]), timeout=timeout)
            if r_stats.returncode == 0 and r_stats.stdout:
                size_bytes = _parse_size_bytes(r_stats.stdout)
                if size_bytes is not None:
                    repo_size_gb = round(size_bytes / (1024**3), 2)

            r_locks = runner.run(_restic_cmd(["list", "locks", "--no-lock"]), timeout=timeout)
            if r_locks.returncode == 0 and r_locks.stdout and r_locks.stdout.strip():
                stale_lock_detected = True
                stale_lock_age_minutes = _parse_lock_age(r_locks.stdout)

        # Probe 4: integrity sampling (optional, disabled by default — can be slow)
        integrity_check_passed: bool | None = None
        integrity_check_errors: str | None = None

        if repo_reachable and config.collectors.restic.integrity_check_enabled:
            subset = config.collectors.restic.data_check_subset_percent
            int_timeout = config.collectors.restic.integrity_timeout_sec
            r_check = runner.run(
                _restic_cmd(["check", f"--read-data-subset={subset}%"]),
                timeout=int_timeout,
            )
            integrity_check_passed = r_check.returncode == 0
            if not integrity_check_passed:
                raw = (r_check.stdout + "\n" + r_check.stderr).strip()
                integrity_check_errors = raw[:500] or None

        signal = ResticSignal(
            last_snapshot_age_hours=last_snapshot_age_hours,
            expected_interval_hours=expected_hours,
            last_exit_code=exit_code,
            last_stderr=stderr if stderr else None,
            repo_reachable=repo_reachable,
            stale_lock_detected=stale_lock_detected,
            stale_lock_age_minutes=stale_lock_age_minutes,
            repo_size_gb=repo_size_gb,
            snapshot_count=snapshot_count,
            repo_path=repo or "$RESTIC_REPOSITORY",
            last_backup_ts=last_ts,
            integrity_check_passed=integrity_check_passed,
            integrity_check_errors=integrity_check_errors,
        )

        success = repo_reachable
        error_message = None if success else (stderr or f"restic exited {exit_code}")

        return CollectorRun(
            collector_id=self.collector_id,
            success=success,
            signals=[signal],
            error_message=error_message,
        )
