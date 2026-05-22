# AIgis Demo Guide

## Pre-Demo Checklist

```bash
# 1. Start backend
python -m aigis serve --host 127.0.0.1 --port 8080

# 2. Start frontend dev server
cd src/aigis/web/frontend && npm run dev

# 3. Seed demo data (22 runs, 24 reports, 5 audit entries)
python scripts/seed_demo.py

# 4. Ensure expired.badssl.com is in SSL domains
curl -s -X PATCH http://127.0.0.1:8080/api/settings \
  -H "Content-Type: application/json" \
  -d '{"ssl_cert_domains": ["google.com", "github.com", "expired.badssl.com"]}'

# 5. Clear run history so LLM doesn't see past failures (important for auto-fix demo)
echo "" > .aigis/run_history.jsonl

# 6. Re-seed after clearing (keeps the demo narrative)
python scripts/seed_demo.py
```

Open `http://localhost:5173` in browser.

---

## Demo Flow (8-10 minutes)

### Act 1: Dashboard Walkthrough (2 min)

1. **Stats strip** — OK / WARN / CRITICAL counters from composite checks across all runs
2. **Checks card** — 9 configured collectors with latest results, shows "Not yet collected" for new ones
3. **Run History chart** — severity timeline Apr 1-9, shows the narrative: healthy → memory spike → endpoint outage → SSL expiry → all resolved
4. **Last Run Analysis** — LLM-generated explanation + reasoning, detected issues with severity badges, suggested actions with Run buttons
5. **Click a run** in history to show the Run Detail page — full check table, analysis breakdown

### Act 2: Live Scan (2 min)

1. Click **Run Scan dropdown** arrow — show the collector picker (all 9 selected, tagged "default")
2. Deselect a couple to show customization, then reset to Default
3. **Run full scan** — watch phase stepper: Collecting → Evaluating → Analyzing → Reporting → Done
4. SSL cert goes **CRITICAL** for `expired.badssl.com`
5. Show the result: check table, LLM analysis explaining the issue, suggested actions

### Act 3: Manual Remediation (1 min)

1. Click **Run** on `check_ssl_cert` — SSE streams real PowerShell output: cert subject, expiry date, days left
2. Click **Run** on `renew_ssl_cert` — streams: tries ACME clients, detects expiry, calls settings API, removes domain from monitoring
3. Close modal — dashboard updates automatically

### Act 4: Verify Fix with Partial Scan (1 min)

1. Click Run Scan dropdown → select **only SSL certificate**
2. Run scan — SSL now shows **OK** (only google.com and github.com checked)
3. Dashboard composite view: SSL OK merged with previous full-scan results — everything green

### Act 5: Auto-Fix Demo (2 min)

1. **Settings** → add `expired.badssl.com` back to SSL domains → Save
2. Check **Auto-fix** checkbox next to Run Scan
3. Run full scan → CRITICAL detected → LLM suggests actions → auto-fix executes `renew_ssl_cert` automatically
4. Show **Audit Log** tab — new entry: `renew_ssl_cert`, `approved_by: auto`, success
5. Run scan again → all green

### Act 6: Configuration (1 min)

1. **Settings page**: target selector (local/homelab/office-vm), LLM model/tokens config
2. **Dynamic collectors**: toggle collectors on/off, all auto-discovered
3. **Collector settings**: HTTP endpoint URLs, SSL domains, thresholds — all editable
4. **Schedule**: cron presets, auto-fix toggle
5. Hot-reload: changes apply immediately via API, no restart

---

## Key Talking Points

### What is AIgis?

A safety-first monitoring and remediation agent for homelab and small-server infrastructure. It collects health signals, evaluates rules, uses Claude for analysis, and executes approved remediation actions — all through a CLI or web dashboard.

### Architecture (one sentence)

**Collect → Evaluate → Analyze → Report → [Auto-fix]** — collectors gather signals via a strategy pattern, a deterministic rules engine evaluates thresholds, Claude reasons about WARN/CRITICAL findings with run history context, and allowlisted shell scripts execute approved remediations.

### What makes it different from Prometheus/Grafana?

AIgis adds an **LLM reasoning layer** on top of threshold monitoring. It doesn't just alert "memory > 80%" — it correlates signals across collectors, explains *why* something is wrong using historical context, suggests specific scripted remediations, and can auto-execute them. Designed for small infra where a full observability stack is overkill.

### Security model

- Actions are **allowlisted** — only registered scripts in config can execute
- Each action has an `auto_approve` flag — destructive actions require manual approval
- Full **audit trail** in JSONL: who approved (auto/tty/web-ui), parameters, exit code, timestamp
- Remote execution via SSH (key or password auth) — no agent installation on targets
- Config validated with Pydantic `extra="forbid"` — rejects unknown fields

---

## Cost Analysis

### Per-scan LLM cost

| Component | Tokens | Cost (Sonnet) |
|-----------|--------|---------------|
| Input (checks + history context) | ~2,000 | $0.006 |
| Output (analysis + actions) | ~500 | $0.005 |
| **Total per scan** | ~2,500 | **~$0.01** |

### Monthly projections

| Schedule | Scans/day | Monthly cost |
|----------|-----------|-------------|
| Every 5 min | 288 | ~$9/mo |
| Every 15 min | 96 | ~$3/mo |
| Every hour | 24 | ~$0.72/mo |
| Manual only | 5-10 | ~$0.10/mo |

### Cost optimization options

- **Disable LLM**: deterministic rules still work, $0 cost
- **Use Haiku**: ~10x cheaper (~$0.001/scan, ~$0.90/mo at 5-min intervals)
- **LLM only on WARN/CRITICAL**: skip analysis when everything is OK (already the default behavior)
- **Adjust schedule**: hourly instead of every 5 min for non-critical infra

### Infrastructure cost

- Runs on any machine with Python 3.12
- No external services except Anthropic API
- No database — JSONL files for history and audit
- ~50 MB disk for a year of run data

---

## Anticipated Questions

### Technical

**Q: How does the composite checks view work?**
The backend merges the last 20 runs' check results, keeping the newest per check_id, filtered to currently enabled collectors. A partial scan (just SSL) updates only that check while preserving others from the last full scan.

**Q: How does it handle remote servers?**
Three Runner implementations: LocalRunner (subprocess), SSHRunner (key auth), SSHPasswordRunner (Paramiko). Commands pipe through `bash -lc` on remote hosts. Targets configured in YAML.

**Q: What about LLM observability?**
Arize Phoenix OTEL tracing built in. Every LLM call is traced with input/output tokens, latency, model info. Dashboard at app.phoenix.arize.com.

**Q: How extensible is it?**
Adding a collector: signal schema + collector class + config + rule evaluator (~50 lines each). Adding an action: a script file + one config entry. Adding an API route: FastAPI router + React component.

### Product

**Q: Can this be used for things other than server monitoring?**
Yes. The pipeline is domain-agnostic: collect signals → evaluate rules → LLM reasons → execute actions. Swap the collectors and you get a different product:

| Domain | Example Collectors |
|--------|-------------------|
| Security monitoring | Open ports, failed logins, CVE scanner |
| Cost optimization | Cloud billing API, idle VMs, storage usage |
| CI/CD health | Build queue, test flake rate, deploy frequency |
| Database monitoring | Slow queries, replication lag, connection pools |
| IoT/Edge fleet | Device heartbeat, firmware version, battery level |
| Compliance auditing | License expiry, access reviews, cert rotation |
| ML model monitoring | Prediction drift, latency p99, data quality |

80% of the code (engine, LLM, actions, audit, dashboard, scheduling) is reusable. Only collectors and action scripts are domain-specific (~50 lines each).

**Q: Why build this instead of using an existing tool?**
Existing tools are either too heavy (Datadog, PagerDuty — enterprise pricing and complexity) or too simple (bash scripts with cron). AIgis sits in the middle: structured monitoring with LLM intelligence, zero infrastructure dependencies, self-hosted, and extensible.

### Business

**Q: What's the target market?**
Homelabbers, small dev teams, indie SaaS operators — anyone running 1-10 servers who wants monitoring smarter than bash scripts but simpler than enterprise tooling.

**Q: What's the moat?**
The collector-agnostic architecture + LLM reasoning layer. As we add more collectors (cloud providers, SaaS APIs, databases), each one benefits from the same analysis engine. Network effects from the knowledge base: remediation patterns learned from one domain transfer to others.

---

## Tech Stack Reference

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic 2 |
| Frontend | React 19, TypeScript 5, Vite 6, TanStack Query, Tailwind CSS |
| LLM | Anthropic Claude (Sonnet default, configurable) |
| Tracing | Arize Phoenix OTEL |
| Remote execution | Paramiko (SSH), subprocess |
| Data storage | JSONL (history, audit), JSON (reports), YAML (config) |
| Package management | uv (Python), npm (frontend) |
