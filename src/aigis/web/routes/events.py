"""SSE event stream — pushes new_run events when the JSONL history file changes."""

import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from aigis.web.dependencies import get_history_path

router = APIRouter()


def _read_last_line(path: Path) -> dict | None:
    """Read the last non-empty line from the JSONL file."""
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    last = line
        if last:
            return json.loads(last)
    except Exception:
        pass
    return None


async def _events_generator(history_path: Path) -> AsyncGenerator[str, None]:
    """Yield SSE events when the run history JSONL changes."""
    try:
        from watchfiles import awatch
    except ImportError:
        yield f"data: {json.dumps({'type': 'error', 'message': 'watchfiles not installed'})}\n\n"
        return

    # Ensure the file exists so watchfiles has something to watch
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if not history_path.exists():
        history_path.touch()

    yield f"data: {json.dumps({'type': 'connected'})}\n\n"

    try:
        async for _ in awatch(str(history_path)):
            entry = _read_last_line(history_path)
            if entry:
                payload = {
                    "type": "new_run",
                    "run_id": entry.get("run_id", ""),
                    "overall_severity": entry.get("overall_severity", "OK"),
                    "timestamp": entry.get("timestamp", ""),
                    "target": entry.get("target", ""),
                }
                yield f"data: {json.dumps(payload)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.get("/events")
async def stream_events(
    history_path: Path = Depends(get_history_path),
) -> StreamingResponse:
    """Long-lived SSE stream that emits new_run events."""
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        _events_generator(history_path),
        media_type="text/event-stream",
        headers=headers,
    )
