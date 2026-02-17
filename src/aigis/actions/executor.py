"""Scripted action executor. Runs allowlisted scripts only."""

import subprocess
from pathlib import Path

from aigis.config import AppConfig
from aigis.schemas.actions import ExecuteResult, SuggestedAction

from aigis.actions.registry import ActionRegistry


def execute_action(
    action: SuggestedAction,
    registry: ActionRegistry,
    config: AppConfig,
) -> ExecuteResult:
    """
    Execute a suggested action via allowlisted script.
    Uses list args, no shell. Returns ExecuteResult.
    """
    valid, err = registry.validate_action(action)
    if not valid:
        return ExecuteResult(success=False, stderr=err, exit_code=-1)

    script_path = registry.get_script_path(action.action_id)
    if script_path is None or not script_path.exists():
        return ExecuteResult(success=False, stderr="Script not found", exit_code=-1)

    param_names = registry.get_param_names(action.action_id)
    args = [str(script_path)]
    for name in param_names:
        val = action.params.get(name)
        if val is not None:
            args.append(str(val))

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=config.actions.timeout_sec,
        )
        return ExecuteResult(
            success=result.returncode == 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return ExecuteResult(
            success=False,
            stderr="Script timed out",
            exit_code=-1,
        )
    except Exception as e:
        return ExecuteResult(
            success=False,
            stderr=str(e),
            exit_code=-1,
        )
