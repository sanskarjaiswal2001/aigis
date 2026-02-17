---
name: aigis
description: Run infrastructure health checks (restic, disk, load, network, docker)
metadata:
  { "openclaw": { "requires": { "bins": ["aigis"] } } }
---

# Aigis Health Check

Run `aigis run` to perform infrastructure health checks. The tool collects signals from:

- Restic backups
- Disk usage
- System load
- Network interfaces
- Docker containers

Output is structured JSON. If severity is WARN or CRITICAL, summarize the failing checks and suggest next steps.
