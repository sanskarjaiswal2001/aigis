"""Configuration loading and validation."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class TargetConfig(BaseModel):
    """Single target host (e.g. for SSH-based remote collection)."""

    model_config = ConfigDict(extra="forbid")

    host: str = ""
    auth: Literal["key", "password"] = "key"
    ssh_key_path: str | None = None
    password: str | None = None


class TargetsConfig(BaseModel):
    """Named targets (hosts) this system can reach."""

    model_config = ConfigDict(extra="forbid")

    homelab: TargetConfig | None = None


class ResticConfig(BaseModel):
    """Restic collector config."""

    model_config = ConfigDict(extra="forbid")

    repo_path: str = ""
    timeout_sec: int = 30
    expected_interval_hours: float = 24.0


class DiskConfig(BaseModel):
    """Disk collector config."""

    model_config = ConfigDict(extra="forbid")

    mounts: list[str] = Field(default_factory=list)


class NetworkConfig(BaseModel):
    """Network collector config."""

    model_config = ConfigDict(extra="forbid")

    interfaces: list[str] = Field(default_factory=list)


class DockerConfig(BaseModel):
    """Docker collector config."""

    model_config = ConfigDict(extra="forbid")

    timeout_sec: int = 10


class CollectorsConfig(BaseModel):
    """Collectors section."""

    model_config = ConfigDict(extra="forbid")

    enabled: list[str] = Field(default_factory=lambda: ["restic", "disk", "load", "network", "docker"])
    restic: ResticConfig = Field(default_factory=ResticConfig)
    disk: DiskConfig = Field(default_factory=DiskConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)


class ResticRulesConfig(BaseModel):
    """Restic rule thresholds."""

    model_config = ConfigDict(extra="forbid")

    warn_hours: float = 24
    critical_hours: float = 48
    stale_lock_warn_minutes: float = 60


class DiskRulesConfig(BaseModel):
    """Disk rule thresholds."""

    model_config = ConfigDict(extra="forbid")

    warn_pct: float = 85
    critical_pct: float = 95


class LoadRulesConfig(BaseModel):
    """Load rule thresholds."""

    model_config = ConfigDict(extra="forbid")

    warn_per_cpu: float = 2.0
    critical_per_cpu: float = 4.0


class RulesConfig(BaseModel):
    """Rules section."""

    model_config = ConfigDict(extra="forbid")

    restic: ResticRulesConfig = Field(default_factory=ResticRulesConfig)
    disk: DiskRulesConfig = Field(default_factory=DiskRulesConfig)
    load: LoadRulesConfig = Field(default_factory=LoadRulesConfig)
    network: dict[str, Any] = Field(default_factory=dict)
    docker: dict[str, Any] = Field(default_factory=dict)


class ReportConfig(BaseModel):
    """Report section."""

    model_config = ConfigDict(extra="forbid")

    output: str = "stdout"
    file_path: str | None = None


class ActionRegistryEntry(BaseModel):
    """Single action registry entry: script path and param names."""

    model_config = ConfigDict(extra="forbid")

    script: str
    params: list[str] = Field(default_factory=list)


class ActionsConfig(BaseModel):
    """Actions section: registry and timeout."""

    model_config = ConfigDict(extra="forbid")

    timeout_sec: int = 60
    registry: dict[str, ActionRegistryEntry] = Field(default_factory=dict)
    audit_log_path: str = "~/.aigis/audit.log"


class PhoenixConfig(BaseModel):
    """Phoenix tracing config for LLM observability."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    endpoint: str = "https://app.phoenix.arize.com/s/phoenix2810/v1/traces"
    project_name: str = "aigis"


class LLMConfig(BaseModel):
    """LLM section."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    model: str = "anthropic/claude-sonnet-4-20250514"
    max_tokens: int = 512
    phoenix: PhoenixConfig = Field(default_factory=PhoenixConfig)


class AppConfig(BaseModel):
    """Full application configuration."""

    model_config = ConfigDict(extra="forbid")

    target: str  # Required: which system to monitor ("local" or key from targets)
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    collectors: CollectorsConfig = Field(default_factory=CollectorsConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    actions: ActionsConfig = Field(default_factory=ActionsConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate config from YAML file."""
    if path is None:
        path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config file required: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    return AppConfig.model_validate(data)
