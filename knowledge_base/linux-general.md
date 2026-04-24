# Linux General — Troubleshooting & Remediation

## High CPU / Runaway Processes

**Diagnose:**
```bash
top -b -n1 | head -20          # snapshot of top processes
ps aux --sort=-%cpu | head -15 # sorted by CPU usage
```

**Remediate:**
```bash
kill -15 <PID>                 # graceful stop (SIGTERM)
kill -9 <PID>                  # force kill (SIGKILL) if SIGTERM is ignored
systemctl restart <service>    # restart if the process is a systemd service
```

**Notes:**
- Always try SIGTERM before SIGKILL.
- Kernel threads (shown in brackets) cannot be killed by users.
- Use `nice` / `renice` to lower priority instead of killing if the process is legitimate.

---

## Memory Pressure

**Diagnose:**
```bash
free -h                        # overview: total, used, free, cached
vmstat -s | grep -E 'memory|swap'
cat /proc/meminfo | grep -E 'MemAvailable|Cached|SwapUsed'
journalctl -k | grep -i "oom"  # check for OOM killer events
```

**Remediate:**
```bash
# Drop page cache (safe, kernel will reclaim as needed)
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Identify top memory consumers
ps aux --sort=-%mem | head -15

# Add swap if none exists
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
```

**Notes:**
- "Available" memory (not "free") is the meaningful metric; Linux uses free RAM for caches.
- OOM killer events indicate genuine memory exhaustion, not just high usage.

---

## Disk Full

**Diagnose:**
```bash
df -h                          # disk usage by filesystem
du -sh /* 2>/dev/null | sort -rh | head -20   # find largest top-level directories
du -sh /var/log/* | sort -rh | head -10       # check logs
```

**Remediate:**
```bash
# Clear old journal logs
sudo journalctl --vacuum-size=500M
sudo journalctl --vacuum-time=7d

# Find and remove large old files
find /var/log -name "*.gz" -mtime +30 -delete
find /tmp -mtime +7 -delete

# Docker cleanup (if Docker is in use)
docker system prune -f
docker volume prune -f
```

**Notes:**
- Never delete files you don't recognize without investigating first.
- `/var/log`, `/tmp`, and Docker volumes are the most common culprits.
- Consider adding logrotate rules if logs grow rapidly.

---

## Systemd Service Failures

**Diagnose:**
```bash
systemctl status <service>           # current state and recent log lines
journalctl -u <service> -n 50        # last 50 log lines for the service
journalctl -u <service> --since "1h ago"  # logs in the past hour
systemctl list-units --failed        # all failed units
```

**Remediate:**
```bash
systemctl restart <service>          # restart the service
systemctl reset-failed <service>     # clear failed state before restarting
systemctl daemon-reload              # reload unit files after editing
systemctl enable <service>           # ensure it starts on boot
```

**Notes:**
- Check `ExecStart` in the unit file (`/etc/systemd/system/<service>.service`) if the command fails.
- `Type=notify` services may fail silently if the notify socket isn't signalled.

---

## SSH Connectivity Issues

**Diagnose (from the remote host):**
```bash
sudo systemctl status sshd
sudo journalctl -u sshd -n 30
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication'
```

**Diagnose (from the client):**
```bash
ssh -v user@host               # verbose — shows exactly where handshake fails
nc -zv host 22                 # check port is reachable
```

**Common fixes:**
```bash
# Key permission issues
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Restart sshd after config change
sudo systemctl restart sshd

# Firewall (ufw)
sudo ufw allow 22/tcp
sudo ufw status
```

**Notes:**
- `StrictModes yes` in sshd_config means `.ssh` directory and files must be owned by the user with tight permissions.
- Never disable `PasswordAuthentication` without ensuring key-based auth works first.

---

## File Permissions

**Diagnose:**
```bash
ls -la /path/to/file           # show owner, group, permissions
stat /path/to/file             # numeric permissions + inode info
getfacl /path/to/file          # show ACLs if in use
```

**Remediate:**
```bash
chmod 644 /path/to/file        # rw-r--r-- (owner read/write, others read)
chmod 755 /path/to/dir         # rwxr-xr-x (directory traversal)
chown user:group /path/to/file # change ownership
chown -R user:group /path/to/dir  # recursive ownership change
```

**Notes:**
- Directories need execute bit (`x`) to be traversable.
- Prefer `chmod` symbolic modes (`u+x`) over octal for clarity.

---

## Cron Jobs Not Running

**Diagnose:**
```bash
crontab -l                     # list current user's cron jobs
sudo crontab -l                # list root's cron jobs
grep CRON /var/log/syslog | tail -20   # cron execution log (Debian/Ubuntu)
journalctl -u cron -n 30       # systemd cron log
```

**Common fixes:**
- Cron does **not** load `~/.bashrc` or `~/.profile`. Use full paths for commands and binaries.
- Add `PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin` at the top of crontab.
- Redirect output to a log file: `* * * * * /path/cmd >> /tmp/cron.log 2>&1`
- Ensure the script has execute permission: `chmod +x /path/to/script.sh`

---

## Network Connectivity

**Diagnose:**
```bash
ping -c 4 8.8.8.8             # basic IP connectivity
curl -I https://example.com   # HTTP reachability
ss -tulpn                     # open ports and listening services
ip addr show                  # interface addresses
ip route show                 # routing table
```

**Remediate:**
```bash
# Restart networking
sudo systemctl restart NetworkManager
sudo systemctl restart networking   # Debian-based without NetworkManager

# Flush and re-acquire DHCP lease
sudo dhclient -r eth0 && sudo dhclient eth0

# Firewall (ufw)
sudo ufw status verbose
sudo ufw allow <port>/tcp
```

**Notes:**
- Check both the local firewall (`ufw`, `iptables`) and any upstream network ACLs.
- `ss -tulpn` shows which process is listening on which port (useful for port conflicts).
