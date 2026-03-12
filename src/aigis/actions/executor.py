"""Scripted action executor. Runs allowlisted scripts only."""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from aigis.config import AppConfig
from aigis.schemas.actions import ExecuteResult, SuggestedAction

from aigis.actions.registry import ActionRegistry

if TYPE_CHECKING:
    from aigis.runner import Runner


def execute_action(
    action: SuggestedAction,
    registry: ActionRegistry,
    config: AppConfig,
    runner: "Runner | None" = None,
) -> ExecuteResult:
    """
    Execute a suggested action via allowlisted script.
    When runner is a remote (SSH) runner, the script is piped to bash on the
    remote host so it runs in the target environment.
    Uses list args, no shell. Returns ExecuteResult.
    """
    valid, err = registry.validate_action(action)
    if not valid:
        return ExecuteResult(success=False, stderr=err, exit_code=-1)

    script_path = registry.get_script_path(action.action_id)
    if script_path is None or not script_path.exists():
        return ExecuteResult(success=False, stderr="Script not found", exit_code=-1)

    param_names = registry.get_param_names(action.action_id)
    positional_args = []
    for name in param_names:
        val = action.params.get(name)
        if val is not None:
            positional_args.append(str(val))

    # Remote execution: pipe script content to bash on the target host.
    # bash -c "content" bash arg1 arg2  →  $1, $2, … receive positional_args.
    # SSHRunner.run() uses bash -lc so ~/.profile is sourced (RESTIC_REPOSITORY etc.).
    if runner is not None and not runner.is_local:
        try:
            script_content = script_path.read_text()
            cmd = ["bash", "-c", script_content, "bash"] + positional_args
            rr = runner.run(cmd, timeout=config.actions.timeout_sec)
            return ExecuteResult(
                success=rr.returncode == 0,
                stdout=rr.stdout,
                stderr=rr.stderr,
                exit_code=rr.returncode,
            )
        except Exception as e:
            return ExecuteResult(success=False, stderr=str(e), exit_code=-1)

    # Local execution.
    args = [str(script_path)] + positional_args
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
