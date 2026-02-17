"""Audit logging for action execution."""

import json
from pathlib import Path
from datetime import datetime

from aigis.config import AppConfig
from aigis.schemas.actions import ExecuteResult, SuggestedAction


def _resolve_audit_path(config: AppConfig) -> Path:
    """Resolve audit log path, expanding ~."""
    path = Path(config.actions.audit_log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def audit_action(
    run_id: str,
    action: SuggestedAction,
    result: ExecuteResult,
    config: AppConfig,
    approved_by: str = "tty",
) -> None:
    """
    Append action execution to audit log (JSONL).
    """
    path = _resolve_audit_path(config)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "action_id": action.action_id,
        "params": action.params,
        "approved_by": approved_by,
        "success": result.success,
        "exit_code": result.exit_code,
    }
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
