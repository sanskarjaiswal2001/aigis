"""Seed demo data: run history, reports, and audit log with a cohesive narrative.

Story:
  Apr 1-3: Everything healthy (OK runs from scheduled cron)
  Apr 4 AM: Memory spike to WARN, disk usage creeping up
  Apr 4 PM: Auto-fix clears disk cache, memory settles
  Apr 5: Back to healthy
  Apr 6: HTTP endpoint (cloudflare.com) goes CRITICAL - timeout
  Apr 6: Auto-fix runs check_endpoint, flush_dns - endpoint recovers
  Apr 7: Healthy again
  Apr 8: SSL cert for expired.badssl.com goes CRITICAL
  Apr 8: check_ssl_cert confirms expiry, renew_ssl_cert removes from monitoring
  Apr 9 AM: All green after SSL remediation
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_PATH = Path(".aigis/run_history.jsonl")
REPORTS_DIR = Path(".aigis/reports")
AUDIT_PATH = Path.home() / ".aigis" / "audit.log"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def rid():
    return uuid.uuid4().hex[:8]


def ts(dt: datetime) -> str:
    return dt.isoformat()


# ── Runs ──────────────────────────────────────────────────────────

base = datetime(2026, 4, 1, 6, 0, 0)
runs = []
audit_entries = []


def make_checks(overrides: dict | None = None) -> list[dict]:
    """Build a standard check list with optional severity/message overrides."""
    defaults = {
        "disk_usage": ("OK", "OK — 62% used", 62.0),
        "system_load": ("OK", "OK", None),
        "memory_usage": ("OK", "OK — 45.8% used (17.2 GB available)", 45.8),
        "cpu_usage": ("OK", "OK — 18.3% used", 18.3),
        "uptime": ("OK", "Up 12d 4h 17m — 1 user(s) logged in", None),
        "http_endpoints": ("OK", "All endpoints reachable", None),
        "ssl_cert": ("OK", "All certificates valid (google.com: 58d, github.com: 120d, expired.badssl.com: OK)", None),
        "windows_services": ("OK", "All watched services running", None),
    }
    names = {
        "disk_usage": "Disk usage",
        "system_load": "System load",
        "memory_usage": "Memory usage",
        "cpu_usage": "CPU usage",
        "uptime": "System uptime",
        "http_endpoints": "HTTP endpoints",
        "ssl_cert": "SSL certificate",
        "windows_services": "Windows services",
    }
    if overrides:
        for k, v in overrides.items():
            defaults[k] = v

    checks = []
    for cid, (sev, msg, val) in defaults.items():
        c = {"check_id": cid, "name": names[cid], "severity": sev, "message": msg}
        if val is not None:
            c["value"] = val
        checks.append(c)
    return checks


def make_run(dt: datetime, severity: str, checks: list[dict],
             explanation: str | None = None,
             reasoning: str | None = None,
             issues: list[dict] | None = None,
             actions: list[dict] | None = None,
             manual: list[dict] | None = None,
             target: str = "local") -> dict:
    run_id = rid()
    timestamp = ts(dt)

    # Determine phases
    phases = [
        {"category": "collection", "description": "Collected 8 signals", "steps": ["disk", "load", "memory", "cpu", "uptime", "http_endpoints", "ssl_cert", "windows_services"], "passes": "true"},
        {"category": "evaluation", "description": f"Evaluated rules: {severity}", "steps": ["All rules evaluated"], "passes": "true"},
    ]
    if explanation:
        phases.append({"category": "analysis", "description": "LLM analysis complete", "steps": ["Anomaly detection", "Action suggestion"], "passes": "true"})
    phases.append({"category": "reporting", "description": "Report generated", "steps": ["JSON output", "History saved"], "passes": "true"})

    history_entry = {
        "run_id": run_id,
        "timestamp": timestamp,
        "target": target,
        "overall_severity": severity,
        "phases": phases,
        "anomaly_explanation": explanation,
    }

    report = {
        "run_id": run_id,
        "timestamp": timestamp,
        "overall_severity": severity,
        "checks": checks,
        "metadata": {},
    }
    if explanation:
        report["anomaly_explanation"] = explanation
    if reasoning:
        report["reasoning_trace"] = reasoning
    if issues:
        report["detected_issues"] = issues
    if actions:
        report["suggested_actions"] = actions
    if manual:
        report["manual_recommendations"] = manual

    runs.append(history_entry)

    # Write report file
    (REPORTS_DIR / f"{run_id}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return run_id


def make_audit(dt: datetime, run_id: str, action_id: str, params: dict,
               approved_by: str, success: bool, exit_code: int = 0):
    audit_entries.append({
        "timestamp": ts(dt),
        "run_id": run_id,
        "action_id": action_id,
        "params": params,
        "approved_by": approved_by,
        "success": success,
        "exit_code": exit_code,
    })


# ── Apr 1: Healthy baseline ──
for h in [6, 12, 18]:
    dt = base.replace(hour=h)
    make_run(dt, "OK", make_checks())

# ── Apr 2: Healthy ──
for h in [6, 12, 18]:
    dt = base.replace(day=2, hour=h)
    make_run(dt, "OK", make_checks({
        "memory_usage": ("OK", "OK — 42.1% used (18.4 GB available)", 42.1),
    }))

# ── Apr 3: Healthy ──
for h in [6, 12, 18]:
    dt = base.replace(day=3, hour=h)
    make_run(dt, "OK", make_checks({
        "cpu_usage": ("OK", "OK — 22.7% used", 22.7),
    }))

# ── Apr 4 AM: Memory WARN + Disk creeping ──
dt4a = base.replace(day=4, hour=8, minute=15)
r4a = make_run(dt4a, "WARN", make_checks({
    "memory_usage": ("WARN", "WARNING — 82.4% used (5.6 GB available)", 82.4),
    "disk_usage": ("OK", "OK — 78% used", 78.0),
    "cpu_usage": ("OK", "OK — 45.2% used", 45.2),
}),
    explanation="Memory usage has spiked to 82.4%, crossing the warning threshold. Disk usage is also elevated at 78%. Possible memory leak in a background process.",
    reasoning="Memory jumped from ~45% baseline to 82.4% — a significant deviation. Disk at 78% is approaching warn threshold (85%). CPU is slightly elevated but within normal range. Recommend clearing disk cache to free space and monitoring memory.",
    issues=[
        {"component": "memory", "severity": "WARN", "explanation": "Memory at 82.4%, exceeding 80% warning threshold"},
    ],
    actions=[
        {"action_id": "clear_disk_cache", "params": {}, "reason": "Free disk space to prevent cascade", "description": "Clear system disk cache to reclaim space"},
    ],
)

# ── Apr 4 PM: Auto-fix executes, things settle ──
make_audit(dt4a + timedelta(minutes=2), r4a, "clear_disk_cache", {}, "auto", True, 0)

dt4b = base.replace(day=4, hour=14, minute=30)
make_run(dt4b, "OK", make_checks({
    "memory_usage": ("OK", "OK — 51.3% used (15.5 GB available)", 51.3),
    "disk_usage": ("OK", "OK — 68% used", 68.0),
}),
    explanation="Memory usage has returned to normal after cache cleanup. Disk freed 10% of space. System stable.",
    reasoning="Memory settled from 82.4% to 51.3% after disk cache clear freed memory pressure. Disk dropped from 78% to 68%. All metrics healthy.",
)

# ── Apr 5: Back to healthy ──
for h in [6, 12, 18]:
    dt = base.replace(day=5, hour=h)
    make_run(dt, "OK", make_checks())

# ── Apr 6 AM: HTTP endpoint CRITICAL ──
dt6a = base.replace(day=6, hour=9, minute=45)
r6a = make_run(dt6a, "CRITICAL", make_checks({
    "http_endpoints": ("CRITICAL", "cloudflare.com: Connection timed out after 10s", None),
}),
    explanation="HTTP endpoint cloudflare.com is unreachable — connection timed out. This could indicate a DNS resolution issue or network connectivity problem.",
    reasoning="Single endpoint failure (cloudflare.com) while google.com and github.com are reachable suggests a DNS or routing issue rather than a full network outage. Recommended: flush DNS cache and re-check endpoint.",
    issues=[
        {"component": "http_endpoints", "severity": "CRITICAL", "explanation": "cloudflare.com unreachable — connection timeout after 10 seconds"},
    ],
    actions=[
        {"action_id": "check_endpoint", "params": {"url": "https://cloudflare.com"}, "reason": "Diagnose connectivity issue", "description": "Run connectivity diagnostics for cloudflare.com"},
        {"action_id": "flush_dns", "params": {}, "reason": "Clear stale DNS cache entries", "description": "Flush DNS resolver cache"},
    ],
)

make_audit(dt6a + timedelta(minutes=1), r6a, "check_endpoint", {"url": "https://cloudflare.com"}, "auto", False, 1)
make_audit(dt6a + timedelta(minutes=2), r6a, "flush_dns", {}, "auto", True, 0)

# ── Apr 6 PM: Endpoint recovered ──
dt6b = base.replace(day=6, hour=15, minute=0)
make_run(dt6b, "OK", make_checks(),
    explanation="HTTP endpoint cloudflare.com is reachable again after DNS flush. All systems healthy.",
    reasoning="DNS flush resolved the cloudflare.com timeout. All endpoints now responding within normal latency. Issue was likely a stale DNS cache entry.",
)

# ── Apr 7: Healthy ──
for h in [6, 12, 18]:
    dt = base.replace(day=7, hour=h)
    make_run(dt, "OK", make_checks())

# ── Apr 8 AM: SSL CRITICAL ──
dt8a = base.replace(day=8, hour=10, minute=20)
r8a = make_run(dt8a, "CRITICAL", make_checks({
    "ssl_cert": ("CRITICAL", "expired.badssl.com: Certificate verification failed: certificate has expired", 0.0),
}),
    explanation="SSL certificate for expired.badssl.com has expired and requires renewal.",
    reasoning="Single CRITICAL issue: expired SSL certificate for expired.badssl.com. All other system metrics are healthy. Certificate renewal is the standard remediation.",
    issues=[
        {"component": "ssl_cert", "severity": "CRITICAL", "explanation": "Certificate for expired.badssl.com failed verification due to expiration"},
    ],
    actions=[
        {"action_id": "check_ssl_cert", "params": {"domain": "expired.badssl.com"}, "reason": "Verify certificate details", "description": "Check certificate status for expired.badssl.com"},
        {"action_id": "renew_ssl_cert", "params": {"domain": "expired.badssl.com"}, "reason": "Renew expired certificate", "description": "Renew expired SSL certificate for expired.badssl.com"},
    ],
)

# User manually triggers check + renew from dashboard
make_audit(dt8a + timedelta(minutes=5), r8a, "check_ssl_cert", {"domain": "expired.badssl.com"}, "web-ui", True, 1)
make_audit(dt8a + timedelta(minutes=8), r8a, "renew_ssl_cert", {"domain": "expired.badssl.com"}, "web-ui", True, 0)

# ── Apr 8 PM: SSL fixed ──
dt8b = base.replace(day=8, hour=16, minute=0)
make_run(dt8b, "OK", make_checks({
    "ssl_cert": ("OK", "All certificates valid (google.com: 57d, github.com: 119d)", None),
}),
    explanation="SSL certificate issue resolved. expired.badssl.com removed from monitoring after renewal attempt. Remaining certificates are healthy.",
    reasoning="Previous SSL cert renewal removed the expired domain from monitoring. google.com (57d) and github.com (119d) certificates are well within validity. All systems operational.",
)

# ── Apr 9 AM: Healthy (today) ──
dt9 = base.replace(day=9, hour=6, minute=0)
make_run(dt9, "OK", make_checks({
    "ssl_cert": ("OK", "All certificates valid (google.com: 56d, github.com: 118d)", None),
    "memory_usage": ("OK", "OK — 47.2% used (16.8 GB available)", 47.2),
}))


# ── Write history ──
with open(HISTORY_PATH, "w", encoding="utf-8") as f:
    for entry in runs:
        f.write(json.dumps(entry) + "\n")

# ── Write audit log ──
with open(AUDIT_PATH, "w", encoding="utf-8") as f:
    for entry in audit_entries:
        f.write(json.dumps(entry) + "\n")

print(f"Created {len(runs)} run history entries")
print(f"Created {len(runs)} report files")
print(f"Created {len(audit_entries)} audit log entries")
