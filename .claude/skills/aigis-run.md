# aigis-run

How to run the aigis project locally for development and production.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend development)
- `.env` file with `ANTHROPIC_API_KEY` (required for LLM features)

## Install Dependencies

```bash
# Python dependencies (core + web + dev)
uv pip install -e ".[web,dev]"

# Frontend dependencies
cd src/aigis/web/frontend && npm install
```

## Running the Full Stack on Port 8080

### Option A: Production Mode (single process)

Build the frontend, then serve everything from FastAPI on port 8080:

```bash
# 1. Build the React SPA into src/aigis/web/static/
cd src/aigis/web/frontend && npm run build

# 2. Start the server — serves API + SPA on port 8080
uv run aigis serve --port 8080
```

FastAPI serves the built SPA via `_mount_static()` in `app.py`. All `/api/*` routes are handled by FastAPI; everything else falls through to `index.html` (SPA fallback).

### Option B: Development Mode (two processes, both on 8080)

Run backend and frontend separately with Vite proxying API calls:

```bash
# Terminal 1: FastAPI backend on port 8080
uv run aigis serve --port 8080

# Terminal 2: Vite dev server on port 5173 (proxies /api → localhost:8080)
cd src/aigis/web/frontend && npm run dev
```

In dev mode, open `http://localhost:5173` for hot-reload. Vite's proxy config in `vite.config.ts` forwards `/api` requests to port 8080.

To serve both on a single port 8080 in dev mode, build the frontend first (Option A).

## CLI Commands

### Health Check (no web server)

```bash
# Run against local machine
uv run aigis

# Run against a configured remote target
uv run aigis --target homelab

# Run with auto-fix (for cron/systemd)
uv run aigis --auto-fix

# Interactive fix mode (TTY required)
uv run aigis --fix
```

### Web Dashboard

```bash
# Default: localhost:8080
uv run aigis serve

# Custom host/port
uv run aigis serve --host 0.0.0.0 --port 8080

# With specific config file
uv run aigis serve --config config/default.yaml --port 8080
```

### Utility Commands

```bash
# Generate encryption key
uv run aigis --generate-key

# Encrypt a password for config
uv run aigis --encrypt-password "my-secret"

# Ingest a file into the knowledge base
uv run aigis --ingest path/to/file.md
```

## Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Specific test file
uv run pytest tests/test_collectors.py -v

# By marker
uv run pytest -m unit
uv run pytest -m integration
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes (for LLM) | Claude API key |
| `AIGIS_KEY` | Optional | Encryption key for passwords in config |
| `OTEL_SDK_DISABLED` | Optional | Set `true` to disable Phoenix tracing |

## Configuration

Main config: `config/default.yaml`

Key sections:
- `collectors.enabled` — which collectors to run
- `llm.enabled` / `llm.model` — LLM analysis settings
- `target` — `local` or a named target from `targets`
- `schedule.cron` — auto-run schedule for web dashboard
- `actions.registry` — available remediation actions

## Key Files

| File | Purpose |
|------|---------|
| `src/aigis/main.py` | CLI entry point, `aigis` command |
| `src/aigis/web/app.py` | FastAPI app factory |
| `src/aigis/web/frontend/vite.config.ts` | Vite config (proxy, build output) |
| `config/default.yaml` | Default configuration |
| `pyproject.toml` | Package definition, dependencies |
