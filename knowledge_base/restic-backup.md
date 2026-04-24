# Restic Backup Issues

## Symptoms
- `restic_backup` check at WARN or CRITICAL
- Repository unreachable, stale lock, or backup older than expected
- `restic_integrity` CRITICAL (data corruption detected)

## Diagnosis

```bash
# Check repo is accessible
restic -r /path/to/repo snapshots

# List recent snapshots
restic -r /path/to/repo snapshots --last 5

# Check for locks
restic -r /path/to/repo list locks

# Run full integrity check
restic -r /path/to/repo check

# Check with data verification (slow)
restic -r /path/to/repo check --read-data-subset=25%

# Repo stats
restic -r /path/to/repo stats
```

## Fixes

### Repository unreachable — wrong password
```bash
# Verify password
echo $RESTIC_PASSWORD
# Re-export and retry
export RESTIC_PASSWORD="correct_password"
restic -r /path/to/repo snapshots
```

### Repository unreachable — permissions
```bash
ls -la /path/to/repo
chmod -R 700 /path/to/repo
chown -R $USER /path/to/repo
```

### Remove stale lock
```bash
# List locks first
restic -r /path/to/repo list locks

# Remove all stale locks (safe if no backup is running)
restic -r /path/to/repo unlock
```

### Run a backup immediately
```bash
restic -r /path/to/repo backup /home /etc /var/www
```

### Repair after data corruption
```bash
# Rebuild index (safe, does not modify pack files)
restic -r /path/to/repo rebuild-index

# Prune dangling packs
restic -r /path/to/repo prune

# Remove snapshots with missing data (last resort)
restic -r /path/to/repo forget --prune --keep-last 5
```

### Initialize a new repository
```bash
restic init --repo /path/to/new/repo
# or for remote (SFTP)
restic init --repo sftp:user@host:/path/to/repo
```

### Automate backups with systemd timer
```ini
# /etc/systemd/system/restic-backup.service
[Service]
Type=oneshot
ExecStart=/usr/bin/restic -r /backup/repo backup /home /etc
Environment=RESTIC_PASSWORD_FILE=/etc/restic/password

# /etc/systemd/system/restic-backup.timer
[Timer]
OnCalendar=daily
Persistent=true
```

## Prevention
- Store `RESTIC_PASSWORD` in a secrets manager or `/etc/restic/password` (chmod 600)
- Schedule daily backups with systemd timer or cron
- Run `restic check --read-data-subset=5%` weekly to detect silent corruption early
- Keep at least 3-2-1: 3 copies, 2 media types, 1 offsite
