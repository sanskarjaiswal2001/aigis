"""Audit log route — read action execution history."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query

from aigis.web.dependencies import get_audit_path

router = APIRouter()


def _read_audit(path: Path, limit: int) -> list[dict[str, Any]]:
    """Read last `limit` entries from the audit JSONL file."""
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


@router.get("/audit")
async def list_audit_entries(
    limit: int = Query(default=100, ge=1, le=1000),
    audit_path: Path = Depends(get_audit_path),
) -> list[dict[str, Any]]:
    """Return the last N audit log entries, most recent last."""
    return _read_audit(audit_path, limit=limit)
