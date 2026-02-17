"""Docker container health collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, DockerSignal


class DockerCollector:
    """Collect Docker container status via docker ps."""

    collector_id = "docker"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        """Collect docker ps output."""
        timeout = config.collectors.docker.timeout_sec

        r = runner.run(
            ["docker", "ps", "-a", "--format", r"{{.ID}}\t{{.Names}}\t{{.State}}\t{{.Status}}\t{{.Health}}"],
            timeout=timeout,
        )
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr[:500] if r.stderr else f"docker exited {r.returncode}",
            )

        signals: list[DockerSignal] = []
        for line in r.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 4)
            cid = parts[0] if len(parts) > 0 else ""
            name = parts[1] if len(parts) > 1 else ""
            state = parts[2] if len(parts) > 2 else ""
            status = parts[3] if len(parts) > 3 else ""
            health = parts[4].strip() if len(parts) > 4 else None
            if health == "" or health == "<nil>":
                health = None
            signals.append(
                DockerSignal(
                    container_id=cid[:12],
                    name=name,
                    state=state,
                    status=status,
                    health=health,
                )
            )

        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )
