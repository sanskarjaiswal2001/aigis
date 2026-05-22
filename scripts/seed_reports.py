"""Generate demo report JSON files matching run history entries."""

import json
from pathlib import Path

REPORTS_DIR = Path(".aigis/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Delete old reports
for f in REPORTS_DIR.glob("*.json"):
    f.unlink()


def check(check_id, name, severity, message, value=None, ref=None):
    r = {"check_id": check_id, "name": name, "severity": severity, "message": message}
    if value is not None:
        r["value"] = value
    if ref is not None:
        r["raw_signal_ref"] = ref
    return r


def action(action_id, params, reason, description=None):
    a = {"action_id": action_id, "params": params, "reason": reason}
    if description:
        a["description"] = description
    return a


def issue(component, severity, explanation):
    return {"component": component, "severity": severity, "explanation": explanation}


def manual(description, risk_level="low"):
    return {"description": description, "risk_level": risk_level}


def report(run_id, ts, severity, checks_list, anomaly=None, reasoning=None,
           issues=None, actions=None, manuals=None):
    r = {
        "run_id": run_id,
        "timestamp": ts,
        "overall_severity": severity,
        "checks": checks_list,
        "metadata": {"duration_ms": 4200, "config_version": "0.1.0"},
    }
    if anomaly:
        r["anomaly_explanation"] = anomaly
    if reasoning:
        r["reasoning_trace"] = reasoning
    if issues:
        r["detected_issues"] = issues
    if actions:
        r["suggested_actions"] = actions
    if manuals:
        r["manual_recommendations"] = manuals
    return r


# Standard OK checks
STD_OK = [
    check("disk_usage", "Disk usage", "OK", "OK"),
    check("system_load", "System load", "OK", "OK"),
    check("memory_usage", "Memory usage", "OK", "OK \u2014 62% used (5.8 GB available)", 62.0),
    check("cpu_usage", "CPU usage", "OK", "OK \u2014 23% used", 23.0),
    check("uptime", "System uptime", "OK", "Up 3d 8h 14m \u2014 1 user(s) logged in"),
]

ENDPOINTS_OK = check("http_endpoints", "HTTP endpoints", "OK", "All endpoints reachable")
SSL_OK = check("ssl_cert", "SSL certificate", "OK", "All certificates valid")


reports = []

# --- Apr 1: Clean baseline ---
reports.append(report("8f1a2b3c4d5e", "2026-04-01T06:00:02.118334", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("9a2b3c4d5e6f", "2026-04-01T18:00:04.221847", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

# --- Apr 2: Endpoint down ---
reports.append(report("a1b2c3d4e5f6", "2026-04-02T03:15:01.339102", "CRITICAL",
    STD_OK + [
        check("http_endpoint", "HTTP endpoint", "CRITICAL",
              "https://api.internal.corp:8443: DOWN \u2014 Connection refused", None, "https://api.internal.corp:8443"),
        SSL_OK,
    ],
    anomaly="Internal API endpoint api.internal.corp:8443 is unreachable. Connection refused suggests the service is down or DNS resolution is stale.",
    reasoning="Endpoint returned connection refused. DNS cache may be stale after recent network changes. Flushing DNS and re-checking is the lowest-risk first step.",
    issues=[
        issue("http_endpoints", "CRITICAL", "api.internal.corp:8443 is unreachable"),
    ],
    actions=[
        action("check_endpoint", {"url": "https://api.internal.corp:8443"}, "Diagnose endpoint connectivity", "Run DNS, TCP, and HTTP diagnostics"),
        action("flush_dns", {}, "Clear stale DNS cache", "Flush local DNS resolver cache"),
    ]))

reports.append(report("a2b3c4d5e6f7", "2026-04-02T06:00:03.441209", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

# --- Apr 3: SSL warning ---
reports.append(report("b1c2d3e4f5a6", "2026-04-03T03:00:02.551823", "WARN",
    STD_OK + [
        ENDPOINTS_OK,
        check("ssl_cert", "SSL certificate", "WARN", "dash.homelab.local: expires in 12d (warn: 30d)", 12.0, "dash.homelab.local"),
    ],
    anomaly="SSL certificate for dash.homelab.local expires in 12 days. Renewal recommended before expiry to avoid service disruption.",
    reasoning="Certificate is within the 30-day warning window. No immediate outage risk but renewal should be scheduled.",
    issues=[issue("ssl_cert", "WARN", "dash.homelab.local cert expires in 12 days")],
    actions=[
        action("check_ssl_cert", {"domain": "dash.homelab.local"}, "Inspect certificate chain and expiry details"),
        action("renew_ssl_cert", {"domain": "dash.homelab.local"}, "Renew certificate via certbot"),
    ]))

reports.append(report("b7c8d9e0f1a2", "2026-04-03T14:30:01.881433", "WARN",
    STD_OK + [
        ENDPOINTS_OK,
        check("ssl_cert", "SSL certificate", "WARN", "dash.homelab.local: expires in 11d (warn: 30d)", 11.0, "dash.homelab.local"),
    ],
    anomaly="SSL certificate for dash.homelab.local is expiring soon (11 days). Certificate inspection and renewal required.",
    reasoning="Continued degradation from 12d to 11d. Human-initiated renewal is the correct remediation.",
    issues=[issue("ssl_cert", "WARN", "dash.homelab.local cert expires in 11 days")],
    actions=[
        action("check_ssl_cert", {"domain": "dash.homelab.local"}, "Verify current certificate state"),
        action("renew_ssl_cert", {"domain": "dash.homelab.local"}, "Renew certificate before expiry"),
    ]))

# --- Apr 4: Clean then Prometheus down ---
reports.append(report("c1d2e3f4a5b6", "2026-04-04T06:00:05.102938", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("c3d4e5f6a7b8", "2026-04-04T22:05:01.920384", "CRITICAL",
    STD_OK + [
        check("docker", "Docker", "CRITICAL", "Container prometheus not running: exited", "exited", "prometheus"),
        check("http_endpoint", "HTTP endpoint", "CRITICAL",
              "https://prometheus.homelab.local:9090: DOWN \u2014 Connection refused", None, "https://prometheus.homelab.local:9090"),
        SSL_OK,
    ],
    anomaly="Prometheus container has exited unexpectedly, causing its HTTP endpoint to become unreachable. Container restart recommended.",
    reasoning="Container state is 'exited' and the corresponding HTTP endpoint is down. These are correlated \u2014 restarting the container should restore both. OOM kill or config error may be root cause.",
    issues=[
        issue("docker", "CRITICAL", "Prometheus container exited unexpectedly"),
        issue("http_endpoints", "CRITICAL", "prometheus.homelab.local:9090 unreachable"),
    ],
    actions=[
        action("restart_container", {"container_name": "prometheus"}, "Restart crashed Prometheus container"),
        action("check_endpoint", {"url": "https://prometheus.homelab.local:9090"}, "Verify endpoint after restart"),
    ],
    manuals=[
        manual("Check container logs: docker logs prometheus --tail 50", "low"),
        manual("Review memory limits in docker-compose.yml if OOM suspected", "low"),
    ]))

# --- Apr 5: Backup + disk warning ---
reports.append(report("d9e0f1a2b3c4", "2026-04-05T06:00:01.448819", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("e5f6a7b8c9d0", "2026-04-05T19:12:01.661542", "WARN",
    [
        check("disk_usage", "Disk usage", "WARN", "C:\\: 87.2% used (warn: 85%)", 87.2, "C:\\"),
        check("system_load", "System load", "OK", "OK"),
        check("memory_usage", "Memory usage", "OK", "OK \u2014 58% used (6.4 GB available)", 58.0),
        check("cpu_usage", "CPU usage", "OK", "OK \u2014 31% used", 31.0),
        check("uptime", "System uptime", "OK", "Up 4d 6h 2m \u2014 1 user(s) logged in"),
        ENDPOINTS_OK, SSL_OK,
    ],
    anomaly="Disk usage on C:\\ has climbed to 87.2%, crossing the warning threshold. Temporary files and package caches are likely contributors.",
    reasoning="Disk crossed 85% warn threshold. No critical services affected yet. Cache clearing is a safe first step.",
    issues=[issue("disk", "WARN", "C:\\ at 87.2% usage, above 85% threshold")],
    actions=[
        action("clear_disk_cache", {}, "Clear temporary files and package caches"),
    ]))

# --- Apr 6: Git SSL critical + Windows service ---
reports.append(report("f1a2b3c4d5e6", "2026-04-06T02:30:01.209738", "CRITICAL",
    STD_OK + [
        ENDPOINTS_OK,
        check("ssl_cert", "SSL certificate", "CRITICAL", "git.homelab.local: expires in 5d (critical: 7d)", 5.0, "git.homelab.local"),
    ],
    anomaly="SSL certificate for git.homelab.local expires in 5 days, below the critical threshold. Immediate renewal required.",
    reasoning="Certificate is within 7-day critical window. All git push/pull operations over HTTPS will fail once it expires. Urgent renewal needed.",
    issues=[issue("ssl_cert", "CRITICAL", "git.homelab.local cert expires in 5 days")],
    actions=[
        action("check_ssl_cert", {"domain": "git.homelab.local"}, "Inspect certificate details and chain"),
        action("renew_ssl_cert", {"domain": "git.homelab.local"}, "Renew certificate immediately"),
    ],
    manuals=[
        manual("Verify certbot auto-renewal timer: systemctl status certbot.timer", "low"),
        manual("Check renewal hooks in /etc/letsencrypt/renewal-hooks/", "low"),
    ]))

reports.append(report("f2a3b4c5d6e7", "2026-04-06T06:00:03.887210", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("a7b8c9d0e1f2", "2026-04-06T14:20:01.991204", "WARN",
    STD_OK + [
        check("windows_service_wuauserv", "Service: Windows Update", "WARN",
              "Service is stopped (start type: auto)", "stopped", "wuauserv"),
        ENDPOINTS_OK, SSL_OK,
    ],
    anomaly="Windows Update service (wuauserv) is stopped despite being configured for automatic start.",
    reasoning="Service has auto start type but is currently stopped. Restarting should restore normal update functionality.",
    issues=[issue("windows_services", "WARN", "Windows Update service stopped unexpectedly")],
    actions=[
        action("restart_service", {"service_name": "wuauserv"}, "Restart Windows Update service"),
    ]))

# --- Apr 7: Routine + expired.badssl.com ---
reports.append(report("b3c4d5e6f7a8", "2026-04-07T03:00:01.402815", "WARN",
    [
        check("disk_usage", "Disk usage", "OK", "OK"),
        check("system_load", "System load", "OK", "OK"),
        check("memory_usage", "Memory usage", "OK", "OK \u2014 55% used (6.9 GB available)", 55.0),
        check("cpu_usage", "CPU usage", "OK", "OK \u2014 18% used", 18.0),
        check("uptime", "System uptime", "OK", "Up 5d 14h 50m \u2014 1 user(s) logged in"),
        ENDPOINTS_OK,
        check("ssl_cert", "SSL certificate", "CRITICAL",
              "expired.badssl.com: Certificate verification failed: certificate has expired", 0, "expired.badssl.com"),
    ],
    anomaly="SSL certificate for expired.badssl.com has expired. This is a known test domain with a deliberately expired certificate \u2014 no action required for production services.",
    reasoning="expired.badssl.com is a public test domain intentionally serving an expired certificate. No production impact."))

reports.append(report("c9d0e1f2a3b4", "2026-04-07T09:45:01.224901", "WARN",
    STD_OK + [
        ENDPOINTS_OK,
        check("ssl_cert", "SSL certificate", "CRITICAL",
              "expired.badssl.com: Certificate verification failed: certificate has expired", 0, "expired.badssl.com"),
    ],
    anomaly="expired.badssl.com certificate remains expired (known test domain). All production certificates are valid.",
    reasoning="Same known-expired test domain. Production certificates verified healthy.",
    actions=[
        action("check_ssl_cert", {"domain": "expired.badssl.com"}, "Confirm certificate status for test domain"),
    ]))

# --- Apr 8: DNS + Grafana ---
reports.append(report("d5e6f7a8b9c0", "2026-04-08T04:15:01.882340", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("e1f2a3b4c5d6", "2026-04-08T18:30:01.109476", "WARN",
    STD_OK + [
        check("docker", "Docker", "WARN", "Container grafana not running: restarting", "restarting", "grafana"),
        check("http_endpoint", "HTTP endpoint", "CRITICAL",
              "https://grafana.homelab.local:3000: DOWN \u2014 Connection refused", None, "https://grafana.homelab.local:3000"),
        SSL_OK,
    ],
    anomaly="Grafana container is in a restart loop, causing its dashboard endpoint to be unreachable.",
    reasoning="Container is cycling between 'restarting' states. HTTP endpoint confirms the service is not accepting connections. Restart and verification needed.",
    issues=[
        issue("docker", "WARN", "Grafana container stuck in restart loop"),
        issue("http_endpoints", "CRITICAL", "grafana.homelab.local:3000 unreachable"),
    ],
    actions=[
        action("restart_container", {"container_name": "grafana"}, "Force restart Grafana container"),
        action("check_endpoint", {"url": "https://grafana.homelab.local:3000"}, "Verify endpoint after restart"),
    ]))

# --- Apr 9: Nightly + clean ---
reports.append(report("f7a8b9c0d1e2", "2026-04-09T03:00:01.553218", "OK",
    STD_OK + [ENDPOINTS_OK, SSL_OK]))

reports.append(report("a8b9c0d1e2f3", "2026-04-09T06:00:02.770318", "OK",
    [
        check("disk_usage", "Disk usage", "OK", "OK"),
        check("system_load", "System load", "OK", "OK"),
        check("memory_usage", "Memory usage", "OK", "OK \u2014 51% used (7.5 GB available)", 51.0),
        check("cpu_usage", "CPU usage", "OK", "OK \u2014 15% used", 15.0),
        check("uptime", "System uptime", "OK", "Up 7d 17h 50m \u2014 1 user(s) logged in"),
        ENDPOINTS_OK, SSL_OK,
    ]))


for r in reports:
    path = REPORTS_DIR / f"{r['run_id']}.json"
    path.write_text(json.dumps(r, indent=2))
    print(f"  {r['run_id']}.json  [{r['overall_severity']}]")

print(f"\nGenerated {len(reports)} reports in {REPORTS_DIR}/")
