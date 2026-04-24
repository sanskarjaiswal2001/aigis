# Disk Space Issues

## Symptoms
- `disk_usage` check at WARN (>85%) or CRITICAL (>95%)
- Applications failing to write logs or temp files
- Package manager errors about no space left

## Diagnosis

Find what's consuming space:
```bash
# Top directories by size
du -h --max-depth=2 / 2>/dev/null | sort -rh | head -20

# Find large files (>500MB)
find / -xdev -type f -size +500M 2>/dev/null

# Check inode usage (can be full even with space available)
df -i

# Largest packages (Debian/Ubuntu)
dpkg-query -Wf '${Installed-Size}\t${Package}\n' | sort -rn | head -20
```

## Fixes

### Clear package manager cache
```bash
# Debian/Ubuntu
apt-get clean
apt-get autoremove --purge

# Arch/Manjaro
pacman -Sc
paccache -rk1
```

### Clear journal logs
```bash
# Keep only last 7 days
journalctl --vacuum-time=7d

# Keep only last 500MB
journalctl --vacuum-size=500M
```

### Clear Docker unused data
```bash
docker system prune -f
docker volume prune -f
# Nuclear option (removes all unused images too)
docker system prune -af
```

### Clear old kernels (Debian/Ubuntu)
```bash
apt-get autoremove --purge
```

### Truncate large log files
```bash
# Safe truncate (does not break open file handles)
truncate -s 0 /var/log/syslog
truncate -s 0 /var/log/auth.log
```

### Restic prune (backup repo growing too large)
```bash
restic -r /path/to/repo forget --keep-last 10 --keep-daily 7 --keep-weekly 4 --prune
```

## Prevention
- Set up `logrotate` for application logs
- Enable automatic Docker cleanup: `docker system prune` in a weekly cron
- Monitor with: `watch -n 60 df -h`
