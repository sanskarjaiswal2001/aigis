"""In-process cron scheduler: runs aigis as a subprocess on a schedule."""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from croniter import croniter

log = logging.getLogger(__name__)

_task: asyncio.Task | None = None


def next_run_iso(cron: str) -> str | None:
    """Return ISO-8601 UTC datetime of the next trigger for a cron expression."""
    try:
        now = datetime.now(timezone.utc)
        return croniter(cron, now).get_next(datetime).isoformat()
    except Exception:
        return None


async def _run_once(config_path: Path, auto_fix: bool) -> None:
    """Spawn aigis subprocess for a scheduled run."""
    # Import here to avoid circular imports

    import aigis.web.routes.scan as scan_mod  # noqa: PLC0415

    if scan_mod._scan_running:
        log.info("Scheduled scan skipped — another scan is already running")
        return

    cmd = [sys.executable, "-m", "aigis"]
    if config_path and config_path.exists():
        cmd += ["--config", str(config_path)]
    if auto_fix:
        cmd.append("--auto-fix")

    subprocess_env = {**os.environ, "OTEL_SDK_DISABLED": "true"}
    scan_mod._scan_running = True
    try:
        log.info("Scheduled scan starting: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=subprocess_env,
        )
        _, _ = await proc.communicate()
        log.info("Scheduled scan finished (exit %s)", proc.returncode)
    except Exception as exc:
        log.error("Scheduled scan error: %s", exc)
    finally:
        scan_mod._scan_running = False


async def _loop(app: object) -> None:
    """Main scheduler loop — re-reads config each cycle to pick up hot-reloads."""
    while True:
        try:
            config = app.state.config  # type: ignore[attr-defined]
            config_path: Path = app.state.config_path  # type: ignore[attr-defined]

            if not config.schedule.enabled:
                await asyncio.sleep(30)
                continue

            cron = config.schedule.cron
            try:
                now = datetime.now(timezone.utc)
                next_dt = croniter(cron, now).get_next(datetime)
                wait_secs = (next_dt - now).total_seconds()
            except Exception as exc:
                log.warning("Bad cron expression %r: %s", cron, exc)
                await asyncio.sleep(60)
                continue

            if wait_secs > 0:
                await asyncio.sleep(wait_secs)

            # Re-check enabled after sleeping (may have been toggled off)
            if not app.state.config.schedule.enabled:  # type: ignore[attr-defined]
                continue

            asyncio.create_task(_run_once(config_path, app.state.config.schedule.auto_fix))  # type: ignore[attr-defined]

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error("Scheduler loop error: %s", exc)
            await asyncio.sleep(30)


def start(app: object) -> None:
    global _task
    _task = asyncio.create_task(_loop(app))
    log.info("Aigis scheduler started")


def stop() -> None:
    global _task
    if _task:
        _task.cancel()
        _task = None
