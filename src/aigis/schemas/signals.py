"""Raw collector output schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResticSignal(BaseModel):
    """Restic backup status signal."""

    model_config = ConfigDict(extra="forbid")

    last_backup_ts: datetime | None = None
    snapshot_count: int = 0
    repo_path: str = ""
    error: str | None = None


class DiskSignal(BaseModel):
    """Disk usage signal per mount."""

    model_config = ConfigDict(extra="forbid")

    mount_point: str = ""
    used_pct: float = 0.0
    used_gb: float = 0.0
    total_gb: float = 0.0
    device: str = ""


class LoadSignal(BaseModel):
    """System load average signal."""

    model_config = ConfigDict(extra="forbid")

    load_1: float = 0.0
    load_5: float = 0.0
    load_15: float = 0.0


class NetworkSignal(BaseModel):
    """Network interface status signal."""

    model_config = ConfigDict(extra="forbid")

    interface: str = ""
    up: bool = False
    addresses: list[str] = []
    latency_ms: float | None = None


class DockerSignal(BaseModel):
    """Docker container status signal."""

    model_config = ConfigDict(extra="forbid")

    container_id: str = ""
    name: str = ""
    state: str = ""
    status: str = ""
    health: str | None = None


class CollectorRun(BaseModel):
    """Result of a single collector run."""

    model_config = ConfigDict(extra="forbid")

    collector_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = False
    signals: list[Any] = []  # ResticSignal | DiskSignal | LoadSignal | NetworkSignal | DockerSignal
    error_message: str | None = None
