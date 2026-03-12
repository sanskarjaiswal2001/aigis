"""Action execution route — trigger registered actions from the web UI."""

import asyncio
import json
import shlex
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aigis.actions import audit_action, execute_action, get_registry
from aigis.config import AppConfig
from aigis.runner import SSHRunner, get_runner
from aigis.schemas.actions import ExecuteResult, SuggestedAction
from aigis.web.dependencies import get_config

router = APIRouter()


class ActionRequest(BaseModel):
    params: dict[str, str | int | float | bool] = {}
    run_id: str = "web"


class ActionResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


@router.post("/actions/{action_id}")
async def trigger_action(
    action_id: str,
    body: ActionRequest,
    config: AppConfig = Depends(get_config),
) -> ActionResponse:
    """Execute a registered action. Runs in executor to avoid blocking the event loop."""
    registry = get_registry(config)
    if action_id not in config.actions.registry:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not in registry")

    action = SuggestedAction(action_id=action_id, params=body.params)
    runner = get_runner(config)

    # execute_action uses subprocess.run (blocking) — offload to thread pool
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: execute_action(action, registry, config, runner=runner),
    )

    audit_action(body.run_id, action, result, config, approved_by="web-ui")

    return ActionResponse(
        success=result.success,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        exit_code=result.exit_code,
    )


async def _action_stream_generator(
    action_id: str,
    body: ActionRequest,
    config: AppConfig,
) -> AsyncGenerator[str, None]:
    """Async generator that runs an action subprocess and yields SSE events."""
    registry = get_registry(config)
    script_path = registry.get_script_path(action_id)
    if script_path is None or not script_path.exists():
        msg = f"Script not found for action '{action_id}'" if script_path is None else f"Script not found: {script_path}"
        yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
        return

    param_names = registry.get_param_names(action_id)
    positional_args = [str(body.params[n]) for n in param_names if n in body.params]

    runner = get_runner(config)
    proc = None

    try:
        if not runner.is_local:
            # Remote: pipe script to bash on the remote host
            script_content = script_path.read_text()
            bash_cmd = ["bash", "-c", script_content, "bash"] + positional_args
            # Build SSH args mirroring SSHRunner
            ssh_args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=30", "-o", "LogLevel=ERROR"]
            if isinstance(runner, SSHRunner) and runner._ssh_key:
                ssh_args += ["-i", runner._ssh_key]
            if isinstance(runner, SSHRunner):
                ssh_args.append(runner._host)
            ssh_args += ["bash", "-lc", shlex.join(bash_cmd)]
            proc = await asyncio.create_subprocess_exec(
                *ssh_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            # Local: run the script directly
            script_content = script_path.read_text()
            cmd = ["bash", "-c", script_content, "bash"] + positional_args
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def drain(stream: asyncio.StreamReader, stream_type: str) -> None:
            async for raw_line in stream:
                line = raw_line.decode(errors="replace").rstrip()
                await queue.put(f"data: {json.dumps({'type': stream_type, 'line': line})}\n\n")
            await queue.put(None)

        assert proc.stdout is not None
        assert proc.stderr is not None

        tasks = [
            asyncio.create_task(drain(proc.stdout, "stdout")),
            asyncio.create_task(drain(proc.stderr, "stderr")),
        ]

        done_count = 0
        while done_count < 2:
            item = await queue.get()
            if item is None:
                done_count += 1
            else:
                yield item

        await proc.wait()
        for task in tasks:
            task.cancel()

        success = proc.returncode == 0
        yield f"data: {json.dumps({'type': 'done', 'exit_code': proc.returncode, 'success': success})}\n\n"

        # Audit after completion
        action = SuggestedAction(action_id=action_id, params=body.params)
        exec_result = ExecuteResult(
            success=success,
            stdout="",
            stderr="",
            exit_code=proc.returncode or 0,
        )
        audit_action(body.run_id, action, exec_result, config, approved_by="web-ui")

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass


@router.post("/actions/{action_id}/stream")
async def stream_action(
    action_id: str,
    body: ActionRequest,
    config: AppConfig = Depends(get_config),
) -> StreamingResponse:
    """Execute a registered action and stream stdout/stderr as SSE events."""
    if action_id not in config.actions.registry:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not in registry")

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        _action_stream_generator(action_id, body, config),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/actions")
async def list_actions(config: AppConfig = Depends(get_config)) -> dict[str, Any]:
    """List all registered actions with their metadata."""
    return {
        action_id: {
            "script": entry.script,
            "params": entry.params,
            "auto_approve": entry.auto_approve,
        }
        for action_id, entry in config.actions.registry.items()
    }
