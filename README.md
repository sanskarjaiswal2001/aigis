# AIgis

A safety-first monitoring agent for homelab and small-server infrastructure.

## What it does

AIgis collects system signals, runs rule-based health checks, and produces structured reports. It monitors:

- Restic backup status
- Disk usage
- System load
- Network status
- Docker/container health

Reports are emitted as JSON with severity levels (OK, WARN, CRITICAL).

## Requirements

- Python 3.11+
- Restic (for backup checks)
- Docker (optional, for container health)

## Installation

```bash
pip install -e .
```

## Usage

```bash
aigis run
```

Output is JSON to stdout.

## License

GPL v3 (copyleft)
