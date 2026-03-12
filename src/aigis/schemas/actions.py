"""Action schemas for suggested fixes and execution results."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ActionId(str, Enum):
    """Predefined action types (extensible)."""

    RESTART_CONTAINER = "restart_container"
    RUN_RESTIC_BACKUP = "run_restic_backup"
    CLEAR_DISK_CACHE = "clear_disk_cache"
    RESTART_SERVICE = "restart_service"


class SuggestedAction(BaseModel):
    """LLM-suggested fix with action id, params, and reason."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    params: dict[str, str | int | float | bool] = {}
    reason: str = ""
    description: str | None = None  # LLM description of what the script does


class ExecuteResult(BaseModel):
    """Result of executing a scripted action."""

    model_config = ConfigDict(extra="forbid")

    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
