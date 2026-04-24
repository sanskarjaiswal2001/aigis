# High System Load

## Symptoms
- `system_load` check at WARN (load/cpu > 2.0) or CRITICAL (load/cpu > 4.0)
- System unresponsive or slow to SSH
- Applications timing out

## Diagnosis

```bash
# Real-time process view
top -b -n 1 | head -30
htop  # if available

# Find CPU-hungry processes
ps aux --sort=-%cpu | head -15

# Check for zombie processes
ps aux | awk '$8 ~ /Z/'

# IO wait (high iowait = disk bottleneck, not CPU)
iostat -x 1 5

# Check which disks are busy
iotop -b -n 3  # if available

# Check memory pressure (high swap = thrashing)
free -h
vmstat 1 5

# Running systemd services consuming CPU
systemctl status --no-pager | grep -E "running|failed"
```

## Fixes

### Kill runaway process
```bash
# Graceful
kill -15 <PID>
# Force
kill -9 <PID>
# By name
pkill -f "process_name"
```

### Restart misbehaving service
```bash
systemctl restart <service-name>
```

### Reduce swappiness (if heavy swapping)
```bash
# Temporary
sysctl vm.swappiness=10
# Permanent: add to /etc/sysctl.d/99-swappiness.conf
echo "vm.swappiness=10" >> /etc/sysctl.d/99-swappiness.conf
```

### Drop filesystem cache (if memory pressure)
```bash
sync && echo 3 > /proc/sys/vm/drop_caches
```

### Limit CPU for a process
```bash
cpulimit -p <PID> -l 50  # limit to 50% CPU
# or use cgroups
systemctl set-property <service> CPUQuota=50%
```

### Renice a process
```bash
renice +10 -p <PID>   # lower priority
```

## Common Causes
- **Compilation jobs** (`make -j$(nproc)`) — use `make -j2` or `nice make`
- **Backup running** — restic/rsync during peak hours; schedule off-peak
- **Docker container loop** — check `docker stats`; restart or remove container
- **Database full table scan** — check slow query log
- **NFS stale mount** — `df -h` hangs; unmount with `umount -l /mount`
