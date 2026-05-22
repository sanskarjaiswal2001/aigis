"""Generate synthetic run history and per-run reports for dashboard dev."""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

REPORTS_DIR = Path(".aigis/reports")
HISTORY_FILE = Path(".aigis/run_history.jsonl")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ── helpers ──────────────────────────────────────────────────────────────────

def run_id() -> str:
    return uuid.uuid4().hex[:12]

def ts(dt: datetime) -> str:
    return dt.isoformat()


# ── per-run report builder ────────────────────────────────────────────────────

def make_report(rid: str, dt: datetime, scenario: str) -> dict:
    """Build a HealthReport dict for the given scenario."""

    base_checks = [
        {
            "check_id": "load_avg",
            "name": "CPU Load Average",
            "severity": "OK",
            "message": "Load avg 0.42 / CPU — within threshold",
            "value": 0.42,
        },
        {
            "check_id": "disk_root",
            "name": "Disk Usage /",
            "severity": "OK",
            "message": "Root filesystem at 51 %",
            "value": 51.0,
        },
        {
            "check_id": "disk_data",
            "name": "Disk Usage /data",
            "severity": "OK",
            "message": "/data filesystem at 63 %",
            "value": 63.0,
        },
        {
            "check_id": "restic_age",
            "name": "Restic Backup Age",
            "severity": "OK",
            "message": "Last backup 6 h ago — within 24 h threshold",
            "value": 6.1,
        },
        {
            "check_id": "network_rx",
            "name": "Network Receive Rate",
            "severity": "OK",
            "message": "eth0 RX 1.2 MB/s — nominal",
            "value": 1.2,
        },
        {
            "check_id": "docker_unhealthy",
            "name": "Docker Unhealthy Containers",
            "severity": "OK",
            "message": "All 7 containers healthy",
            "value": 0,
        },
    ]

    severity = "OK"
    anomaly_explanation = None
    reasoning_trace = None
    detected_issues = None
    suggested_actions = None
    manual_recommendations = None

    if scenario == "ok":
        pass  # defaults above are fine

    elif scenario == "warn_disk":
        base_checks[1] = {
            "check_id": "disk_root",
            "name": "Disk Usage /",
            "severity": "WARN",
            "message": "Root filesystem at 87 % — approaching 95 % critical threshold",
            "value": 87.0,
        }
        severity = "WARN"
        anomaly_explanation = (
            "Root filesystem utilisation has risen from 51 % yesterday to 87 % today, "
            "an unusually fast climb. Primary contributors appear to be container log "
            "accumulation in /var/lib/docker/containers and a growing Prometheus TSDB "
            "under /var/lib/prometheus. No other collector shows abnormal behaviour."
        )
        reasoning_trace = (
            "1. Disk check fired WARN at 87 %. Threshold is 85 %.\n"
            "2. Checked collector metrics: /var/lib/docker grew +18 GB in 24 h.\n"
            "3. Compared against 7-day trend — previous peak was 72 %.\n"
            "4. No corresponding CPU or memory spike; isolated to disk.\n"
            "5. Suggested clearing old container logs as lowest-risk first step."
        )
        detected_issues = [
            {
                "id": "disk_root_growth",
                "title": "Rapid root filesystem growth",
                "severity": "WARN",
                "detail": "/var/lib/docker/containers grew ~18 GB in the last 24 h. Docker log rotation may not be configured.",
            }
        ]
        suggested_actions = [
            {
                "action_id": "clear_disk_cache",
                "params": {"mount": "/"},
                "reason": "Remove stale container logs to recover disk headroom",
                "description": "Runs `docker system prune --volumes -f` to reclaim space from stopped containers, unused images, and volumes.",
            }
        ]
        manual_recommendations = [
            {
                "description": "Configure Docker daemon log rotation: set `log-opts.max-size=50m` and `max-file=3` in /etc/docker/daemon.json",
                "risk_level": "low",
            }
        ]

    elif scenario == "warn_backup":
        base_checks[3] = {
            "check_id": "restic_age",
            "name": "Restic Backup Age",
            "severity": "WARN",
            "message": "Last backup 31 h ago — stale (threshold: 24 h)",
            "value": 31.0,
        }
        severity = "WARN"
        anomaly_explanation = (
            "The last successful Restic snapshot is 31 hours old, breaching the 24-hour "
            "freshness threshold. Backup jobs have been running but the most recent "
            "snapshot metadata suggests the overnight cron job may have silently failed."
        )
        reasoning_trace = (
            "1. Restic age check fired WARN: 31 h > 24 h threshold.\n"
            "2. Previous runs show consistent 6–8 h backup intervals.\n"
            "3. Stale lock file was not detected — repo is accessible.\n"
            "4. Most likely cause: cron job at 02:00 failed silently (no stderr capture).\n"
            "5. Recommended immediate manual backup followed by cron review."
        )
        detected_issues = [
            {
                "id": "backup_overdue",
                "title": "Backup overdue by 7 hours",
                "severity": "WARN",
                "detail": "Last snapshot: 31 h ago. Scheduled interval: 24 h. Silent cron failure suspected.",
            }
        ]
        suggested_actions = [
            {
                "action_id": "run_restic_backup",
                "params": {},
                "reason": "Trigger an immediate backup to restore freshness SLA",
                "description": "Executes restic backup with the repo and password configured in the environment.",
            }
        ]

    elif scenario == "critical":
        base_checks[1] = {
            "check_id": "disk_root",
            "name": "Disk Usage /",
            "severity": "CRITICAL",
            "message": "Root filesystem at 96 % — above 95 % critical threshold",
            "value": 96.0,
        }
        base_checks[5] = {
            "check_id": "docker_unhealthy",
            "name": "Docker Unhealthy Containers",
            "severity": "WARN",
            "message": "2 of 7 containers reporting unhealthy status: prometheus, grafana",
            "value": 2,
        }
        severity = "CRITICAL"
        anomaly_explanation = (
            "Root filesystem has reached 96 %, triggering a CRITICAL alert. Two Docker "
            "containers (prometheus, grafana) are simultaneously in unhealthy state, likely "
            "caused by failed writes to full disk. Immediate disk reclamation is required to "
            "restore service stability. Prometheus TSDB may have corrupted WAL segments."
        )
        reasoning_trace = (
            "1. Disk CRITICAL: 96 % on /. Two containers unhealthy simultaneously.\n"
            "2. High correlation — disk full → container write failures → health checks fail.\n"
            "3. Prometheus WAL is write-heavy; corruption risk if disk was full during flush.\n"
            "4. Grafana typically recovers after prometheus restarts cleanly.\n"
            "5. Priority: free disk space, then restart containers in order: prometheus → grafana."
        )
        detected_issues = [
            {
                "id": "disk_critical",
                "title": "Root filesystem critically full",
                "severity": "CRITICAL",
                "detail": "96 % utilisation. Risk of write failures across all services.",
            },
            {
                "id": "containers_unhealthy",
                "title": "Prometheus and Grafana unhealthy",
                "severity": "WARN",
                "detail": "Health checks failing, likely due to failed disk writes. Services may be serving stale data.",
            },
        ]
        suggested_actions = [
            {
                "action_id": "clear_disk_cache",
                "params": {"mount": "/"},
                "reason": "Emergency disk reclamation — system is critically full",
                "description": "Runs docker system prune to remove stopped containers, dangling images, and unused volumes.",
            },
            {
                "action_id": "restart_container",
                "params": {"container": "prometheus"},
                "reason": "Restart prometheus after disk space is freed to clear WAL state",
                "description": "docker restart prometheus",
            },
            {
                "action_id": "restart_container",
                "params": {"container": "grafana"},
                "reason": "Restart grafana after prometheus is healthy",
                "description": "docker restart grafana",
            },
        ]
        manual_recommendations = [
            {
                "description": "Configure Prometheus retention: set --storage.tsdb.retention.size=20GB to cap disk usage automatically.",
                "risk_level": "low",
            },
            {
                "description": "Set up a disk full alerting rule in Prometheus at 80 % to catch growth before it reaches critical.",
                "risk_level": "low",
            },
        ]

    elif scenario == "warn_load":
        base_checks[0] = {
            "check_id": "load_avg",
            "name": "CPU Load Average",
            "severity": "WARN",
            "message": "Load avg 2.31 / CPU — above warn threshold of 2.0",
            "value": 2.31,
        }
        severity = "WARN"
        anomaly_explanation = (
            "CPU load average has been elevated at 2.31 per core for the past collection window. "
            "This exceeds the 2.0/CPU warning threshold. Container inspection shows the 'transcoder' "
            "container consuming 340% CPU, likely processing a large media batch job."
        )
        reasoning_trace = (
            "1. Load avg check fired WARN: 2.31 > 2.0 per-CPU threshold.\n"
            "2. System has 4 CPUs; raw load avg ~9.2.\n"
            "3. Cross-referenced docker stats: transcoder container at 340 % CPU.\n"
            "4. This is likely expected batch work, not a runaway process.\n"
            "5. No action recommended unless sustained beyond 2 h or crosses CRITICAL threshold."
        )
        detected_issues = [
            {
                "id": "high_cpu_load",
                "title": "Elevated CPU load average",
                "severity": "WARN",
                "detail": "transcoder container consuming ~340 % CPU. Likely a transient media encoding batch.",
            }
        ]
        manual_recommendations = [
            {
                "description": "Add CPU limits to the transcoder container (e.g. --cpus=2) to prevent it from saturating the host during batch jobs.",
                "risk_level": "low",
            }
        ]

    report = {
        "run_id": rid,
        "timestamp": ts(dt),
        "overall_severity": severity,
        "checks": base_checks,
        "anomaly_explanation": anomaly_explanation,
        "reasoning_trace": reasoning_trace,
        "detected_issues": detected_issues,
        "suggested_actions": suggested_actions,
        "manual_recommendations": manual_recommendations,
        "metadata": {
            "duration_ms": random.randint(800, 4200),
            "config_version": "0.1.0",
            "collector_count": 5,
        },
    }
    # strip None values to match exclude_none=True behaviour
    return {k: v for k, v in report.items() if v is not None}


# ── run history entry builder ─────────────────────────────────────────────────

def make_history_entry(report: dict, target: str = "local") -> dict:
    severity = report["overall_severity"]
    phases = [
        {
            "category": "collection",
            "description": "Collected metrics from 5 collectors",
            "steps": ["disk", "load", "network", "docker", "restic"],
            "passes": "true",
        },
        {
            "category": "evaluation",
            "description": f"Evaluated {len(report['checks'])} checks",
            "steps": [c["check_id"] for c in report["checks"]],
            "passes": "true" if severity == "OK" else "false",
        },
        {
            "category": "analysis",
            "description": "LLM analysis completed" if report.get("anomaly_explanation") else "LLM analysis skipped (disabled)",
            "steps": [],
            "passes": "true",
        },
        {
            "category": "reporting",
            "description": "Report written to .aigis/reports/",
            "steps": [],
            "passes": "true",
        },
    ]
    entry = {
        "run_id": report["run_id"],
        "timestamp": report["timestamp"],
        "target": target,
        "overall_severity": severity,
        "phases": phases,
    }
    if report.get("anomaly_explanation"):
        entry["anomaly_explanation"] = report["anomaly_explanation"]
    return entry


# ── generate runs ─────────────────────────────────────────────────────────────

now = datetime.now()

# Fixed IDs for runs where an action was executed — lets audit entries reference them
CRITICAL_RID  = run_id()
BACKUP_RID    = run_id()

# Manual runs in strict chronological order (all offsets are absolute hours/minutes before now)
runs = [
    # Routine morning check — all clear
    (now - timedelta(hours=81, minutes=14),  "ok",          None),
    # Noticed disk was climbing that afternoon
    (now - timedelta(hours=64, minutes=37),  "warn_disk",   None),
    # Checked again ~75 min later after investigating
    (now - timedelta(hours=63, minutes=22),  "warn_disk",   None),
    # Next morning — disk hit critical  ← actions executed after this run
    (now - timedelta(hours=56, minutes=3),   "critical",    CRITICAL_RID),
    # Re-scan 38 min later after docker prune + container restarts
    (now - timedelta(hours=55, minutes=25),  "warn_disk",   None),
    # Confirmed recovery ~40 min after that
    (now - timedelta(hours=54, minutes=48),  "ok",          None),
    # Backup stale — noticed late evening  ← action executed after this run
    (now - timedelta(hours=21, minutes=19),  "warn_backup", BACKUP_RID),
    # Re-scan 29 min later after triggering backup
    (now - timedelta(hours=20, minutes=50),  "ok",          None),
    # Load spike this morning
    (now - timedelta(hours=5,  minutes=22),  "warn_load",   None),
    # Still elevated 27 min later
    (now - timedelta(hours=4,  minutes=55),  "warn_load",   None),
    # Batch finished — all clear
    (now - timedelta(hours=3,  minutes=10),  "ok",          None),
]

history_lines = []

for dt, scenario, fixed_rid in runs:
    rid = fixed_rid if fixed_rid else run_id()
    report = make_report(rid, dt, scenario)
    entry = make_history_entry(report, target="local")

    report_path = REPORTS_DIR / f"{rid}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    history_lines.append(json.dumps(entry))
    print(f"  {ts(dt)[:19]}  {scenario:<14}  {rid}  {report['overall_severity']}")

HISTORY_FILE.write_text("\n".join(history_lines) + "\n", encoding="utf-8")
print(f"\nWrote {len(runs)} runs to {HISTORY_FILE}")
print(f"Wrote {len(runs)} reports to {REPORTS_DIR}/")

# ── audit log ─────────────────────────────────────────────────────────────────
# Actions executed via the web UI after the CRITICAL and warn_backup runs.

AUDIT_FILE = Path.home() / ".aigis" / "audit.log"
AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

critical_dt = now - timedelta(hours=56, minutes=3)
backup_dt   = now - timedelta(hours=21, minutes=19)

audit_entries = [
    # After the CRITICAL disk run: user ran all three suggested actions from the UI
    {
        "timestamp": ts(critical_dt + timedelta(minutes=8)),
        "run_id": CRITICAL_RID,
        "action_id": "clear_disk_cache",
        "params": {"mount": "/"},
        "approved_by": "web-ui",
        "success": True,
        "exit_code": 0,
    },
    {
        "timestamp": ts(critical_dt + timedelta(minutes=14)),
        "run_id": CRITICAL_RID,
        "action_id": "restart_container",
        "params": {"container": "prometheus"},
        "approved_by": "web-ui",
        "success": True,
        "exit_code": 0,
    },
    {
        "timestamp": ts(critical_dt + timedelta(minutes=17)),
        "run_id": CRITICAL_RID,
        "action_id": "restart_container",
        "params": {"container": "grafana"},
        "approved_by": "web-ui",
        "success": True,
        "exit_code": 0,
    },
    # After the warn_backup run: user triggered a manual backup
    {
        "timestamp": ts(backup_dt + timedelta(minutes=6)),
        "run_id": BACKUP_RID,
        "action_id": "run_restic_backup",
        "params": {},
        "approved_by": "web-ui",
        "success": True,
        "exit_code": 0,
    },
]

AUDIT_FILE.write_text(
    "\n".join(json.dumps(e) for e in audit_entries) + "\n",
    encoding="utf-8",
)
print(f"Wrote {len(audit_entries)} audit entries to {AUDIT_FILE}")
