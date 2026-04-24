# Docker Container Issues

## Symptoms
- `docker` check at WARN — container not running or unhealthy
- Container in `exited`, `dead`, or `restarting` state
- Container health check failing

## Diagnosis

```bash
# Overview of all containers
docker ps -a

# Container resource usage
docker stats --no-stream

# Inspect a specific container
docker inspect <container_name>

# Recent logs (last 100 lines)
docker logs --tail=100 <container_name>

# Follow logs live
docker logs -f <container_name>

# Check exit code of stopped container
docker inspect <container_name> --format '{{.State.ExitCode}}'

# Check health status
docker inspect <container_name> --format '{{.State.Health.Status}}'

# Events in last hour
docker events --since 1h --until now
```

## Fixes

### Restart a stopped/unhealthy container
```bash
docker restart <container_name>
```

### Container keeps restarting (crash loop)
```bash
# Check logs for error
docker logs --tail=50 <container_name>

# Stop the restart loop to examine
docker update --restart=no <container_name>
docker stop <container_name>

# Fix config/env, then re-enable restart
docker update --restart=unless-stopped <container_name>
docker start <container_name>
```

### Out of memory (OOM killed, exit code 137)
```bash
# Check available memory
free -h

# Increase container memory limit (docker-compose.yml)
# services:
#   myapp:
#     mem_limit: 512m

# Or for a running container
docker update --memory="512m" --memory-swap="1g" <container_name>
```

### Disk full — container log too large
```bash
# Check log file size
docker inspect --format='{{.LogPath}}' <container_name>
du -sh $(docker inspect --format='{{.LogPath}}' <container_name>)

# Truncate log (safe)
truncate -s 0 $(docker inspect --format='{{.LogPath}}' <container_name>)

# Set log rotation in daemon.json
# /etc/docker/daemon.json:
# { "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

### Remove and recreate container
```bash
docker stop <container_name>
docker rm <container_name>
docker run -d --name <container_name> --restart=unless-stopped <image>
# or with compose:
docker compose down && docker compose up -d
```

### Fix failing health check
```bash
# View health check command
docker inspect <container_name> --format '{{.Config.Healthcheck}}'

# Check what the health check sees
docker exec <container_name> <health_check_command>

# Temporarily disable health check
docker run --no-healthcheck ...
```

### Pull updated image
```bash
docker pull <image>:<tag>
docker compose pull && docker compose up -d
```

## Prevention
- Always set `--restart=unless-stopped` or `restart: unless-stopped` in compose
- Set log rotation in `/etc/docker/daemon.json`
- Set memory limits to prevent OOM from affecting the whole host
- Use health checks in Dockerfiles: `HEALTHCHECK CMD curl -f http://localhost/ || exit 1`
