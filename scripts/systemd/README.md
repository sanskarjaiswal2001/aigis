# Aigis systemd timer

Runs `aigis --auto-fix` every 15 minutes via systemd timer (replaces raw cron).

Advantages over cron:
- Logs to journald (`journalctl -u aigis.service`)
- `Persistent=true` catches up missed runs after reboot
- `RandomizedDelaySec` prevents multiple hosts hitting the same schedule simultaneously
- `systemctl status aigis.timer` shows last run time and next trigger

## Install

1. Edit `aigis.service` — update `WorkingDirectory` and `ExecStart` to match your install path:
   ```
   WorkingDirectory=/path/to/aigis
   ExecStart=/path/to/aigis/.venv/bin/aigis --auto-fix
   EnvironmentFile=/path/to/aigis/.env
   ```

2. Copy and enable:
   ```bash
   sudo cp aigis.service aigis.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now aigis.timer
   ```

3. Verify:
   ```bash
   systemctl status aigis.timer
   systemctl list-timers aigis.timer
   journalctl -u aigis.service -f
   ```

4. Trigger a manual run:
   ```bash
   sudo systemctl start aigis.service
   ```

## Auto-fix behaviour

With `--auto-fix`, actions marked `auto_approve: true` in `config/default.yaml` execute
automatically when LLM confidence meets the `auto_fix_min_confidence` threshold.
Actions marked `auto_approve: false` (e.g. `restart_container`) are logged in the report
but never executed unattended — they require a human running `aigis --fix` in a terminal.

All auto-executed actions are recorded in `~/.aigis/audit.log` with `approved_by: auto`.
