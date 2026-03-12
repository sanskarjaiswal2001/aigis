"""Run history API routes."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from aigis.web.dependencies import get_history_path, get_reports_dir

router = APIRouter()


def _read_history(path: Path, limit: int) -> list[dict[str, Any]]:
    """Read last `limit` entries from the run history JSONL file."""
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries[-limit:] if len(entries) > limit else entries
    except Exception:
        return []


# NOTE: /runs/latest MUST be registered before /runs/{run_id} to prevent
# "latest" being captured as a run_id path parameter.

@router.get("/runs/latest")
async def get_latest_run(
    history_path: Path = Depends(get_history_path),
) -> dict[str, Any]:
    entries = _read_history(history_path, limit=1)
    if not entries:
        raise HTTPException(status_code=404, detail="No runs yet")
    return entries[-1]


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=50, ge=1, le=500),
    history_path: Path = Depends(get_history_path),
) -> list[dict[str, Any]]:
    return _read_history(history_path, limit=limit)


@router.get("/runs/{run_id}/report")
async def get_run_report(
    run_id: str,
    reports_dir: Path = Depends(get_reports_dir),
) -> dict[str, Any]:
    report_file = reports_dir / f"{run_id}.json"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail=f"Report not found for run {run_id}")
    try:
        return json.loads(report_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
