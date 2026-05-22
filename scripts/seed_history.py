"""Generate demo run history entries matching the audit log narrative."""

import json
import sys

entries = []


def entry(run_id, ts, target, severity, collectors, checks, anomaly=None, healing=None, suggested_count=0):
    phases = []
    # Collection
    coll_steps = []
    coll_details = {}
    for cid, ok in collectors:
        status = "success" if ok else "failed"
        coll_steps.append(f"Ran collector: {cid} ({status})")
        coll_details[cid] = ok
    phases.append({
        "category": "collection",
        "description": "Gather metrics from enabled collectors",
        "steps": coll_steps,
        "passes": "true" if all(ok for _, ok in collectors) else "false",
        "details": coll_details,
    })
    # Evaluation
    eval_steps = []
    eval_details = {}
    has_crit = False
    for check_id, sev, msg in checks:
        eval_steps.append(f"Evaluated {check_id} \u2192 {sev}: {msg}")
        eval_details[check_id] = sev
        if sev == "CRITICAL":
            has_crit = True
    phases.append({
        "category": "evaluation",
        "description": "Evaluate rules against collected signals",
        "steps": eval_steps,
        "passes": "false" if has_crit else "true",
        "details": eval_details,
    })
    # Reporting
    phases.append({
        "category": "reporting",
        "description": "Build health report and overall severity",
        "steps": [f"Built report run_id={run_id}", f"Overall severity: {severity}"],
        "passes": "true",
    })
    # Analysis
    phases.append({
        "category": "analysis",
        "description": "LLM explanation and suggested fixes",
        "steps": [
            "LLM analysis: anomaly_explanation present" if anomaly else "LLM analysis: skipped or none",
            f"Suggested {suggested_count} actions",
        ],
        "passes": "true",
        "details": {"suggested_count": suggested_count},
    })
    # Healing
    if healing:
        h_steps = [f"Executed {aid} ({'success' if ok else 'failed'})" for aid, ok in healing]
        h_details = {aid: ok for aid, ok in healing}
        phases.append({
            "category": "healing",
            "description": "Apply suggested actions after human approval",
            "steps": h_steps,
            "passes": "true" if all(ok for _, ok in healing) else "false",
            "details": h_details,
        })
    return {
        "run_id": run_id,
        "timestamp": ts,
        "target": target,
        "overall_severity": severity,
        "phases": phases,
        "anomaly_explanation": anomaly,
    }


STD_COLLECTORS = [
    ("disk", True), ("load", True), ("network", True), ("memory", True),
    ("cpu", True), ("http_endpoints", True), ("uptime", True), ("ssl_cert", True),
]

STD_CHECKS_OK = [
    ("disk_usage", "OK", "OK"),
    ("system_load", "OK", "OK"),
    ("memory_usage", "OK", "OK \u2014 62% used (5.8 GB available)"),
    ("cpu_usage", "OK", "OK \u2014 23% used"),
    ("uptime", "OK", "Up 3d 8h 14m \u2014 1 user(s) logged in"),
]

DOCKER_COLLECTORS = [
    ("disk", True), ("load", True), ("network", True), ("memory", True),
    ("cpu", True), ("docker", True), ("http_endpoints", True), ("uptime", True), ("ssl_cert", True),
]

WINSVC_COLLECTORS = [
    ("disk", True), ("load", True), ("network", True), ("memory", True),
    ("cpu", True), ("windows_services", True), ("http_endpoints", True), ("uptime", True), ("ssl_cert", True),
]

# --- Apr 1: Clean baseline ---
entries.append(entry("8f1a2b3c4d5e", "2026-04-01T06:00:02.118334", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))

entries.append(entry("9a2b3c4d5e6f", "2026-04-01T18:00:04.221847", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))

# --- Apr 2 03:15: Endpoint down -> DNS flush -> fixed (audit: a1b2c3d4e5f6) ---
entries.append(entry("a1b2c3d4e5f6", "2026-04-02T03:15:01.339102", "local", "CRITICAL",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoint", "CRITICAL", "https://api.internal.corp:8443: DOWN \u2014 Connection refused"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    anomaly="Internal API endpoint api.internal.corp:8443 is unreachable. Connection refused suggests the service is down or DNS resolution is stale. Recommend endpoint diagnosis and DNS cache flush.",
    suggested_count=2,
    healing=[("check_endpoint", False), ("flush_dns", True), ("check_endpoint", True)]))

entries.append(entry("a2b3c4d5e6f7", "2026-04-02T06:00:03.441209", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))

# --- Apr 3: SSL warning on dash.homelab.local (audit: b7c8d9e0f1a2) ---
entries.append(entry("b1c2d3e4f5a6", "2026-04-03T03:00:02.551823", "local", "WARN",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "WARN", "dash.homelab.local: expires in 12d (warn: 30d)"),
    ],
    anomaly="SSL certificate for dash.homelab.local expires in 12 days. Renewal recommended before expiry to avoid service disruption.",
    suggested_count=2))

entries.append(entry("b7c8d9e0f1a2", "2026-04-03T14:30:01.881433", "local", "WARN",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "WARN", "dash.homelab.local: expires in 11d (warn: 30d)"),
    ],
    anomaly="SSL certificate for dash.homelab.local is expiring soon (11 days). Certificate inspection and renewal required.",
    suggested_count=2,
    healing=[("check_ssl_cert", False), ("renew_ssl_cert", True), ("check_ssl_cert", True)]))

# --- Apr 4: Clean, then Prometheus down (audit: c3d4e5f6a7b8) ---
entries.append(entry("c1d2e3f4a5b6", "2026-04-04T06:00:05.102938", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))

entries.append(entry("c3d4e5f6a7b8", "2026-04-04T22:05:01.920384", "local", "CRITICAL",
    DOCKER_COLLECTORS,
    STD_CHECKS_OK + [
        ("docker", "CRITICAL", "Container prometheus not running: exited"),
        ("http_endpoint", "CRITICAL", "https://prometheus.homelab.local:9090: DOWN \u2014 Connection refused"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    anomaly="Prometheus container has exited unexpectedly, causing its HTTP endpoint to become unreachable. Container restart recommended. Root cause may be OOM kill or configuration error.",
    suggested_count=2,
    healing=[("restart_container", False), ("restart_container", True), ("check_endpoint", True)]))

# --- Apr 5: Backup + disk warning (audit: d9e0f1a2b3c4, e5f6a7b8c9d0) ---
entries.append(entry("d9e0f1a2b3c4", "2026-04-05T06:00:01.448819", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    healing=[("run_restic_backup", True)]))

entries.append(entry("e5f6a7b8c9d0", "2026-04-05T19:12:01.661542", "local", "WARN",
    STD_COLLECTORS,
    [
        ("disk_usage", "WARN", "C:\\: 87.2% used (warn: 85%)"),
        ("system_load", "OK", "OK"),
        ("memory_usage", "OK", "OK \u2014 58% used (6.4 GB available)"),
        ("cpu_usage", "OK", "OK \u2014 31% used"),
        ("uptime", "OK", "Up 4d 6h 2m \u2014 1 user(s) logged in"),
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    anomaly="Disk usage on C:\\ has climbed to 87.2%, crossing the warning threshold. Temporary files and package caches are likely contributors. Cache clearing recommended.",
    suggested_count=1,
    healing=[("clear_disk_cache", True)]))

# --- Apr 6: Git SSL critical + Windows service (audit: f1a2b3c4d5e6, a7b8c9d0e1f2) ---
entries.append(entry("f1a2b3c4d5e6", "2026-04-06T02:30:01.209738", "local", "CRITICAL",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "CRITICAL", "git.homelab.local: expires in 5d (critical: 7d)"),
    ],
    anomaly="SSL certificate for git.homelab.local expires in 5 days, below the critical threshold. Immediate renewal required to prevent service disruption for all git operations.",
    suggested_count=2,
    healing=[("check_ssl_cert", False), ("renew_ssl_cert", False), ("renew_ssl_cert", True), ("check_ssl_cert", True)]))

entries.append(entry("f2a3b4c5d6e7", "2026-04-06T06:00:03.887210", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))

entries.append(entry("a7b8c9d0e1f2", "2026-04-06T14:20:01.991204", "local", "WARN",
    WINSVC_COLLECTORS,
    STD_CHECKS_OK + [
        ("windows_service_wuauserv", "WARN", "Service is stopped (start type: auto)"),
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    anomaly="Windows Update service (wuauserv) is stopped despite being configured for automatic start. Restarting the service to restore update functionality.",
    suggested_count=1,
    healing=[("restart_service", True)]))

# --- Apr 7: Routine + expired.badssl.com (audit: b3c4d5e6f7a8, c9d0e1f2a3b4) ---
entries.append(entry("b3c4d5e6f7a8", "2026-04-07T03:00:01.402815", "local", "WARN",
    STD_COLLECTORS,
    [
        ("disk_usage", "OK", "OK"),
        ("system_load", "OK", "OK"),
        ("memory_usage", "OK", "OK \u2014 55% used (6.9 GB available)"),
        ("cpu_usage", "OK", "OK \u2014 18% used"),
        ("uptime", "OK", "Up 5d 14h 50m \u2014 1 user(s) logged in"),
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "CRITICAL", "expired.badssl.com: Certificate verification failed: certificate has expired"),
    ],
    anomaly="SSL certificate for expired.badssl.com has expired. This is a known test domain with a deliberately expired certificate \u2014 no action required for production services."))

entries.append(entry("c9d0e1f2a3b4", "2026-04-07T09:45:01.224901", "local", "WARN",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "CRITICAL", "expired.badssl.com: Certificate verification failed: certificate has expired"),
    ],
    anomaly="expired.badssl.com certificate remains expired (known test domain). All production certificates are valid.",
    suggested_count=1,
    healing=[("check_ssl_cert", False)]))

# --- Apr 8: DNS maintenance + Grafana restart (audit: d5e6f7a8b9c0, e1f2a3b4c5d6) ---
entries.append(entry("d5e6f7a8b9c0", "2026-04-08T04:15:01.882340", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    healing=[("flush_dns", True), ("check_endpoint", True)]))

entries.append(entry("e1f2a3b4c5d6", "2026-04-08T18:30:01.109476", "local", "WARN",
    DOCKER_COLLECTORS,
    STD_CHECKS_OK + [
        ("docker", "WARN", "Container grafana not running: restarting"),
        ("http_endpoint", "CRITICAL", "https://grafana.homelab.local:3000: DOWN \u2014 Connection refused"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    anomaly="Grafana container is in a restart loop, causing its dashboard endpoint to be unreachable. Container restart and endpoint verification recommended.",
    suggested_count=2,
    healing=[("restart_container", True), ("check_endpoint", True)]))

# --- Apr 9: Nightly maintenance + latest clean (audit: f7a8b9c0d1e2) ---
entries.append(entry("f7a8b9c0d1e2", "2026-04-09T03:00:01.553218", "local", "OK",
    STD_COLLECTORS,
    STD_CHECKS_OK + [
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ],
    healing=[("run_restic_backup", True), ("clear_disk_cache", True)]))

entries.append(entry("a8b9c0d1e2f3", "2026-04-09T06:00:02.770318", "local", "OK",
    STD_COLLECTORS,
    [
        ("disk_usage", "OK", "OK"),
        ("system_load", "OK", "OK"),
        ("memory_usage", "OK", "OK \u2014 51% used (7.5 GB available)"),
        ("cpu_usage", "OK", "OK \u2014 15% used"),
        ("uptime", "OK", "Up 7d 17h 50m \u2014 1 user(s) logged in"),
        ("http_endpoints", "OK", "All endpoints reachable"),
        ("ssl_cert", "OK", "All certificates valid"),
    ]))


for e in entries:
    print(json.dumps(e))
