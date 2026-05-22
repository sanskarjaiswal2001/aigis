#!/usr/bin/env python3
"""
Aigis Screenshot Generator
---------------------------
Injects rich demo data (history, reports, audit log) then launches the server
and takes 1920x1080 Playwright screenshots of every dashboard view.

Usage:
    uv run python demo/screenshot.py

Output: demo/screenshots/*.png
"""

import asyncio
import json
import shutil
import urllib.request
from pathlib import Path

SERVER_PORT = 8080
SERVER_URL = f"http://localhost:{SERVER_PORT}"
OUT_DIR = Path("demo/screenshots")

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

HISTORY_PATH = Path(".aigis/run_history.jsonl")
AUDIT_PATH = Path.home() / ".aigis" / "audit.log"
REPORTS_DIR = Path(".aigis/reports")

LATEST_RUN_ID = "f3a9c2d1"
TARGET = "production-server"

HISTORY_ENTRIES = [
    # oldest → newest
    {"run_id": "a0b1c2d3", "timestamp": "2026-04-06T06:11:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "b1c2d3e4", "timestamp": "2026-04-07T06:09:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "c2d3e4f5", "timestamp": "2026-04-08T06:12:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "d3e4f5a6", "timestamp": "2026-04-09T06:08:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk usage at 71% on /var/lib/postgresql. Approaching threshold — monitor closely."},
    {"run_id": "e4f5a6b7", "timestamp": "2026-04-10T06:10:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "f5a6b7c8", "timestamp": "2026-04-11T06:07:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "a6b7c8d9", "timestamp": "2026-04-12T06:13:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk at 78%. PostgreSQL WAL directory growing. Recommend monitoring autovacuum."},
    {"run_id": "b7c8d9e0", "timestamp": "2026-04-14T06:11:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "c8d9e0f1", "timestamp": "2026-04-16T06:09:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk at 83%. WAL accumulation continues. Container api-gateway showing elevated restart count."},
    {"run_id": "d9e0f1a2", "timestamp": "2026-04-18T06:14:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk at 86%. System load elevated at 5.4. Suggested WAL cleanup was not executed."},
    {"run_id": "e0f1a2b3", "timestamp": "2026-04-20T06:10:00", "target": TARGET, "overall_severity": "CRITICAL", "phases": [], "anomaly_explanation": "Disk at 89% — approaching critical threshold. postgres-db container now unhealthy. Immediate intervention required."},
    {"run_id": "f1a2b3c4", "timestamp": "2026-04-22T06:08:00", "target": TARGET, "overall_severity": "OK",       "phases": [], "anomaly_explanation": None},
    {"run_id": "a2b3c4d5", "timestamp": "2026-04-24T06:12:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk at 88% — WAL accumulation resumed after brief recovery. Container api-gateway restarted 3 times in last hour."},
    {"run_id": "b3c4d5e6", "timestamp": "2026-04-26T06:09:00", "target": TARGET, "overall_severity": "WARN",     "phases": [], "anomaly_explanation": "Disk at 90%. Load average elevated. Two consecutive WARN runs — escalating to CRITICAL threshold imminent."},
    {
        "run_id": LATEST_RUN_ID,
        "timestamp": "2026-04-28T10:45:00",
        "target": TARGET,
        "overall_severity": "CRITICAL",
        "phases": [
            {
                "category": "collection",
                "description": "Gather metrics from enabled collectors",
                "steps": [
                    "Ran collector: restic (success)",
                    "Ran collector: disk (success)",
                    "Ran collector: load (success)",
                    "Ran collector: docker (success)",
                    "Ran collector: network (success)",
                ],
                "passes": "true",
                "details": {"restic": True, "disk": True, "load": True, "docker": True, "network": True},
            },
            {
                "category": "evaluation",
                "description": "Evaluate rules against collected signals",
                "steps": [
                    "Evaluated disk_usage → CRITICAL: /var/lib/postgresql at 92% (460 GB / 500 GB)",
                    "Evaluated docker_health → WARN: postgres-db is unhealthy (health check failing for 18 min)",
                    "Evaluated system_load → WARN: load_5=6.8 exceeds warn threshold of 6.0 on 4-core system",
                    "Evaluated restic_backup → OK: Last snapshot 7.2 hours ago",
                    "Evaluated network_status → OK: All interfaces up",
                ],
                "passes": "false",
                "details": {
                    "disk_usage": "CRITICAL",
                    "docker_health": "WARN",
                    "system_load": "WARN",
                    "restic_backup": "OK",
                    "network_status": "OK",
                },
            },
            {
                "category": "reporting",
                "description": "Build health report and overall severity",
                "steps": [
                    f"Built report run_id={LATEST_RUN_ID}",
                    "Overall severity: CRITICAL",
                ],
                "passes": "true",
            },
            {
                "category": "analysis",
                "description": "LLM explanation and suggested fixes",
                "steps": [
                    "LLM analysis: anomaly_explanation present",
                    "Suggested 3 actions",
                ],
                "passes": "true",
                "details": {"suggested_count": 3},
            },
        ],
        "anomaly_explanation": (
            "PostgreSQL data volume at 92% — 40 GB remaining. "
            "Combined with an unhealthy postgres-db container (health check failing for 18 minutes) "
            "and elevated system load (6.8 on a 4-core host), this pattern strongly indicates "
            "WAL segment accumulation caused by a stalled replication slot or a long-running transaction "
            "preventing autovacuum from reclaiming dead tuples. This is the fourth consecutive run showing "
            "disk growth, and the container health degradation is a new escalation signal."
        ),
    },
]

LATEST_REPORT = {
    "run_id": LATEST_RUN_ID,
    "timestamp": "2026-04-28T10:45:00",
    "overall_severity": "CRITICAL",
    "checks": [
        {"check_id": "disk_usage",     "name": "Disk Usage",       "severity": "CRITICAL", "message": "/var/lib/postgresql at 92% (460 GB / 500 GB)", "value": 92.0},
        {"check_id": "docker_health",  "name": "Docker Health",    "severity": "WARN",     "message": "postgres-db is unhealthy — health check failing for 18 min", "value": None},
        {"check_id": "system_load",    "name": "System Load",      "severity": "WARN",     "message": "load_5=6.8 exceeds warn threshold 6.0 (4 cores)", "value": 6.8},
        {"check_id": "restic_backup",  "name": "Restic Backup",    "severity": "OK",       "message": "Last snapshot 7.2 hours ago — within 24h interval", "value": None},
        {"check_id": "network_status", "name": "Network Status",   "severity": "OK",       "message": "All interfaces up (eth0, eth1)", "value": None},
    ],
    "collected_metrics": {
        "disk": [{"mount_point": "/var/lib/postgresql", "used_pct": 92.0, "used_gb": 460.0, "total_gb": 500.0, "device": "/dev/sdb1"}],
        "load": [{"load_1": 7.2, "load_5": 6.8, "load_15": 5.9}],
        "docker": [
            {"container_id": "a1b2c3d4e5f6", "name": "postgres-db",  "state": "running", "status": "Up 2 hours (unhealthy)", "health": "unhealthy"},
            {"container_id": "b2c3d4e5f6a7", "name": "api-gateway",  "state": "running", "status": "Up 14 hours",             "health": "healthy"},
            {"container_id": "c3d4e5f6a7b8", "name": "redis-cache",  "state": "running", "status": "Up 3 days",               "health": "healthy"},
            {"container_id": "d4e5f6a7b8c9", "name": "prometheus",   "state": "running", "status": "Up 3 days",               "health": None},
        ],
        "restic": [{"repo_path": "/mnt/backups/postgres", "last_snapshot_age_hours": 7.2, "snapshot_count": 84, "repo_size_gb": 120.4, "stale_lock_detected": False}],
        "network": [
            {"interface": "eth0", "up": True, "addresses": ["10.0.1.50/24"], "latency_ms": 0.4},
            {"interface": "eth1", "up": True, "addresses": ["192.168.100.1/24"], "latency_ms": None},
        ],
    },
    "anomaly_explanation": (
        "PostgreSQL data volume at 92% — 40 GB remaining. "
        "Combined with an unhealthy postgres-db container (health check failing for 18 minutes) "
        "and elevated system load (6.8 on a 4-core host), this pattern strongly indicates "
        "WAL segment accumulation caused by a stalled replication slot or a long-running transaction "
        "preventing autovacuum from reclaiming dead tuples. This is the fourth consecutive run showing "
        "disk growth, and the container health degradation is a new escalation signal."
    ),
    "reasoning_trace": (
        "Disk at 92% with an unhealthy database container points to internal bloat rather than application data growth — "
        "the backup repo (120 GB) is healthy and network is clean, ruling out external factors. "
        "The load spike (6.8) correlates with autovacuum competing for I/O against normal query load. "
        "Stalled replication slots are the highest-probability cause: they prevent WAL removal even after checkpoints. "
        "Recommended intervention order: (1) identify and drop stalled slots, (2) force VACUUM on bloated tables, "
        "(3) restart container to clear in-memory health check state, (4) trigger a fresh backup once disk recovers below 80%."
    ),
    "detected_issues": [
        {"severity": "CRITICAL", "check_id": "disk_usage",    "message": "/var/lib/postgresql at 92% (460 GB / 500 GB) — 40 GB remaining"},
        {"severity": "WARN",     "check_id": "docker_health",  "message": "postgres-db container health check failing for 18 minutes"},
        {"severity": "WARN",     "check_id": "system_load",    "message": "5-minute load average 6.8 on 4-core host (threshold: 6.0)"},
    ],
    "suggested_actions": [
        {
            "action_id": "cleanup_postgres_wal",
            "params": {"container": "postgres-db"},
            "reason": "Drop stalled replication slots and force WAL checkpoint to reclaim disk space immediately.",
            "description": "Connects to the PostgreSQL instance and drops any stalled replication slots, then runs CHECKPOINT to flush WAL segments.",
        },
        {
            "action_id": "restart_container",
            "params": {"name": "postgres-db"},
            "reason": "Container health check has been failing for 18 minutes — a clean restart will reset connection state and health check counters.",
            "description": "Gracefully stops and restarts the named Docker container.",
        },
        {
            "action_id": "run_restic_backup",
            "params": {"repo": "/mnt/backups/postgres"},
            "reason": "Trigger a fresh backup after WAL cleanup to confirm data integrity before disk pressure continues.",
            "description": "Runs a restic backup for the specified repository path.",
        },
    ],
    "manual_recommendations": [
        {"description": "Review pg_replication_slots and terminate any inactive slots (SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE active = false)", "risk_level": "medium"},
        {"description": "Check autovacuum activity: SELECT relname, last_autovacuum, n_dead_tup FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10", "risk_level": "low"},
    ],
    "metadata": {"duration_ms": 4820, "config_version": "1.3.0", "collectors_run": 5},
}

AUDIT_ENTRIES = [
    {
        "timestamp": "2026-04-20T06:18:42",
        "run_id": "e0f1a2b3",
        "action_id": "cleanup_postgres_wal",
        "params": {"container": "postgres-db"},
        "approved_by": "operator",
        "success": True,
        "exit_code": 0,
        "stdout": "Dropped 2 stalled replication slots.\nCHECKPOINT executed. WAL directory reduced from 28 GB to 4 GB.\n",
        "stderr": "",
        "duration_ms": 3210,
    },
    {
        "timestamp": "2026-04-20T06:19:05",
        "run_id": "e0f1a2b3",
        "action_id": "restart_container",
        "params": {"name": "postgres-db"},
        "approved_by": "operator",
        "success": True,
        "exit_code": 0,
        "stdout": "Container postgres-db stopped.\nContainer postgres-db started.\nHealth check passed after 12s.\n",
        "stderr": "",
        "duration_ms": 15800,
    },
    {
        "timestamp": "2026-04-20T06:19:22",
        "run_id": "e0f1a2b3",
        "action_id": "run_restic_backup",
        "params": {"repo": "/mnt/backups/postgres"},
        "approved_by": "operator",
        "success": True,
        "exit_code": 0,
        "stdout": "snapshot abc12345 saved\nAdded: 2.145 GiB\nDuration: 48.3s\n",
        "stderr": "",
        "duration_ms": 48300,
    },
    {
        "timestamp": "2026-04-24T06:21:10",
        "run_id": "a2b3c4d5",
        "action_id": "cleanup_postgres_wal",
        "params": {"container": "postgres-db"},
        "approved_by": "operator",
        "success": True,
        "exit_code": 0,
        "stdout": "Dropped 1 stalled replication slot.\nCHECKPOINT executed. WAL directory reduced from 18 GB to 2 GB.\n",
        "stderr": "",
        "duration_ms": 2890,
    },
    {
        "timestamp": "2026-04-26T06:23:55",
        "run_id": "b3c4d5e6",
        "action_id": "restart_container",
        "params": {"name": "api-gateway"},
        "approved_by": "operator",
        "success": False,
        "exit_code": 1,
        "stdout": "",
        "stderr": "Error: container api-gateway failed to start: port 8080 already in use\n",
        "duration_ms": 5100,
    },
]


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def write_demo_data() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        for entry in HISTORY_ENTRIES:
            f.write(json.dumps(entry) + "\n")

    report_path = REPORTS_DIR / f"{LATEST_RUN_ID}.json"
    report_path.write_text(json.dumps(LATEST_REPORT, indent=2), encoding="utf-8")

    with AUDIT_PATH.open("w", encoding="utf-8") as f:
        for entry in AUDIT_ENTRIES:
            f.write(json.dumps(entry) + "\n")

    print(f"  Demo data written: {len(HISTORY_ENTRIES)} runs, {len(AUDIT_ENTRIES)} audit entries")


async def start_server() -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        "uv", "run", "aigis", "serve",
        "--host", "127.0.0.1", "--port", str(SERVER_PORT),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )


async def wait_for_server(timeout_s: int = 40) -> bool:
    print("  Waiting for server...", end="", flush=True)
    for _ in range(timeout_s * 4):
        try:
            urllib.request.urlopen(f"{SERVER_URL}/api/runs", timeout=1)
            print(" ready.")
            return True
        except Exception:
            await asyncio.sleep(0.25)
    print(" TIMEOUT.")
    return False


# ---------------------------------------------------------------------------
# Screenshot runner
# ---------------------------------------------------------------------------

async def take_screenshots() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = await ctx.new_page()

        async def goto(url: str, sleep: float = 2.0) -> None:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(sleep)

        async def click_nav(name: str, sleep: float = 2.0) -> None:
            await page.get_by_role("link", name=name).click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(sleep)

        # --- Dashboard ---
        await goto(SERVER_URL, sleep=2.5)
        await page.screenshot(path=str(OUT_DIR / "dashboard.png"), full_page=False)
        print("  dashboard.png")

        # --- Runs list ---
        await click_nav("Runs", sleep=1.5)
        await page.screenshot(path=str(OUT_DIR / "runs.png"), full_page=False)
        print("  runs.png")

        # --- Run detail ---
        await page.locator("tbody tr").first.get_by_role("link").click()
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1.5)
        await page.screenshot(path=str(OUT_DIR / "run_detail_top.png"), full_page=False)
        print("  run_detail_top.png")

        # Scroll to suggested actions
        await page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'})")
        await asyncio.sleep(0.5)
        await page.screenshot(path=str(OUT_DIR / "run_detail_actions.png"), full_page=False)
        print("  run_detail_actions.png")

        # Full page run detail
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await asyncio.sleep(0.3)
        await page.screenshot(path=str(OUT_DIR / "run_detail_full.png"), full_page=True)
        print("  run_detail_full.png")

        # --- Audit log ---
        await click_nav("Audit Log", sleep=1.5)
        await page.screenshot(path=str(OUT_DIR / "audit.png"), full_page=False)
        print("  audit.png")

        # --- Settings ---
        await click_nav("Settings", sleep=1.5)
        await page.screenshot(path=str(OUT_DIR / "settings.png"), full_page=False)
        print("  settings.png")

        await browser.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("\n=== Aigis Screenshot Generator ===\n")

    print("[1/3] Writing demo data...")
    write_demo_data()

    print("[2/3] Starting server...")
    server = await start_server()
    try:
        if not await wait_for_server():
            print("ERROR: server failed to start")
            return

        print(f"[3/3] Taking screenshots -> {OUT_DIR}/")
        await take_screenshots()

        print(f"\nDone. {len(list(OUT_DIR.glob('*.png')))} screenshots in {OUT_DIR}/")
    finally:
        server.terminate()
        try:
            await asyncio.wait_for(server.wait(), timeout=5)
        except asyncio.TimeoutError:
            server.kill()


if __name__ == "__main__":
    asyncio.run(main())
