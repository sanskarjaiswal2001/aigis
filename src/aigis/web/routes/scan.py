"""Scan trigger route — runs aigis as a subprocess and streams output via SSE."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aigis.web.dependencies import get_config_path

router = APIRouter()

# Global lock: only one scan at a time
_scan_lock = asyncio.Lock()


class ScanRequest(BaseModel):
    auto_fix: bool = False
    target: str | None = None


async def _scan_generator(
    req: ScanRequest,
    config_path: Path,
) -> AsyncGenerator[str, None]:
    """Async generator that runs aigis and yields SSE events."""
    cmd = [sys.executable, "-m", "aigis"]
    if config_path and config_path.exists():
        cmd += ["--config", str(config_path)]
    if req.target:
        cmd += ["--target", req.target]
    if req.auto_fix:
        cmd.append("--auto-fix")

    # Disable OTEL in the subprocess: the batch span exporter otherwise emits
    # "Failed to export span batch" on process shutdown, which pollutes scan output.
    subprocess_env = {**os.environ, "OTEL_SDK_DISABLED": "true"}

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=subprocess_env,
        )

        async def read_lines(stream: asyncio.StreamReader, stream_type: str) -> AsyncGenerator[str, None]:
            async for raw_line in stream:
                line = raw_line.decode(errors="replace").rstrip()
                yield f"data: {json.dumps({'type': stream_type, 'line': line})}\n\n"

        # Stream stdout and stderr concurrently using asyncio queues
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def drain(stream: asyncio.StreamReader, stream_type: str) -> None:
            async for event in read_lines(stream, stream_type):
                await queue.put(event)
            await queue.put(None)  # sentinel

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

        yield f"data: {json.dumps({'type': 'done', 'exit_code': proc.returncode})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        # Kill the subprocess if the client disconnected before it finished,
        # otherwise an orphaned process would write a duplicate history entry.
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        _scan_lock.release()


@router.post("/scan")
async def trigger_scan(
    req: ScanRequest,
    config_path: Path = Depends(get_config_path),
) -> StreamingResponse:
    """Trigger an aigis scan and stream stdout/stderr as SSE events."""
    if _scan_lock.locked():
        raise HTTPException(status_code=409, detail="A scan is already running")

    await _scan_lock.acquire()
    # Lock is released inside the generator (finally block)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        _scan_generator(req, config_path),
        media_type="text/event-stream",
        headers=headers,
    )
