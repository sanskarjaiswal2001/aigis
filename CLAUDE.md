# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Aigis** is a safety-first monitoring agent for homelab/small-server infrastructure. It collects system signals, evaluates them against configurable rules, produces structured health reports, and optionally uses Claude AI to explain anomalies and suggest fixes — with human approval before executing any remediation.

## Commands

```bash
# Install dependencies
uv sync

# Run monitoring pipeline
aigis run
aigis run --config config/default.yaml
aigis run --target homelab
aigis run --fix                   # Enable LLM analysis, approval prompt, and action execution

# Run tests
pytest
pytest tests/test_collectors.py  # Single file
pytest -k "test_restic"          # Single test by name

# Alternative entry point
python -m aigis
```

## Architecture

The pipeline runs in this order: **Collection → Evaluation → Reporting → LLM Analysis (optional) → Healing (optional) → History**

```
Collectors → CollectorRun[] → Rules Engine → CheckResult[] → ReportBuilder → HealthReport
                                                                      ↓
                                                         LLM Analyzer (Claude)
                                                         anomaly_explanation + suggested_actions[]
                                                                      ↓
                                                         Human Approval → Action Executor → Audit Log
                                                                      ↓
                                                         Run History (.aigis/run_history.jsonl)
```

### Key Source Locations

- `src/aigis/main.py` — Facade/orchestrator for the full pipeline; start here
- `src/aigis/collectors/` — Pluggable data sources (restic, disk, load, network, docker), each producing typed signals via the `Collector` protocol
- `src/aigis/engine/` — Deterministic rule evaluation; each collector has a matching evaluator with WARN/CRITICAL thresholds
- `src/aigis/llm/` — Single Claude API call for anomaly explanation + fix suggestions; includes Phoenix OTEL tracing
- `src/aigis/actions/` — Registry of shell scripts (from config), executor with timeouts, audit log
- `src/aigis/approval/` — CLI prompt for human sign-off before executing suggested actions
- `src/aigis/schemas/` — All Pydantic models: signals, checks, reports, actions, run history
- `src/aigis/report/` — Assembles `HealthReport` and renders Markdown
- `config/default.yaml` — Primary config (targets, collectors, rules thresholds, LLM, actions, run history)

### Runner Abstraction

Commands are run via one of three runners (selected by config):
- `LocalRunner` — `subprocess.run` for local execution
- `SSHRunner` — `subprocess ssh` for key-based remote
- `SSHPasswordRunner` — `paramiko` for password-based remote

### Data Flow Types

Collectors produce **signals** (`ResticSignal`, `DiskSignal`, `LoadSignal`, `NetworkSignal`, `DockerSignal`). The engine evaluates signals into **`CheckResult[]`** with `Severity` (OK/WARN/CRITICAL). These feed `HealthReport`, which carries `overall_severity`, `anomaly_explanation`, and `suggested_actions`.

### Run History

Persisted to `.aigis/run_history.jsonl`. Previous N runs are loaded and passed to the LLM for continuity — allowing it to notice recurring issues or confirm that a fix worked.

## Configuration

The config YAML supports:
- `target`: which host to monitor (`local` or a named entry in `targets`)
- `targets`: SSH host definitions with auth method (`key`, `password`, `agent`)
- `collectors`: enabled list + per-collector settings (restic repo path, disk mounts, docker timeout)
- `rules`: per-collector WARN/CRITICAL thresholds
- `llm`: enabled flag, model, max_tokens, Phoenix tracing endpoint
- `actions`: scripts registry (path + accepted params), audit log path
- `run_history`: JSONL path, `last_n_runs` for LLM context window

## Environment

Requires `.env` with:
```
ANTHROPIC_API_KEY=sk-ant-...
AIGIS_KEY=<fernet-key>        # Required when any target uses password auth
```

Python 3.12+ required. Uses `uv` as the package manager.

## Password Encryption

Passwords in config are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256). The key lives only in `.env` (never in config or version control).

**One-time setup:**
```bash
aigis --generate-key           # prints AIGIS_KEY=... → paste into .env
aigis --encrypt-password "pw"  # prints enc:<token>   → paste into config
```

**Config format:**
```yaml
targets:
  my-server:
    auth: password
    password: enc:gAAAAAB...   # encrypted value from --encrypt-password
```

At config load time, `TargetConfig` auto-decrypts any `enc:` prefixed password via `src/aigis/crypto.py`. Plain-text passwords (no prefix) still work but print a deprecation warning.
