"""Settings route — read and update editable config fields."""

import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from aigis.config import load_config
from aigis.web.dependencies import get_config, get_config_path

router = APIRouter()

# All known collector ids
_ALL_COLLECTORS = ["restic", "disk", "load", "network", "docker"]
_CONFIDENCE_LEVELS = ["low", "medium", "high"]


class SettingsResponse(BaseModel):
    # Target
    active_target: str
    available_targets: list[str]
    target_host: str
    target_auth: str
    # LLM
    llm_enabled: bool
    llm_model: str
    llm_max_tokens: int
    llm_api_key_configured: bool
    # Collectors
    collectors_enabled: list[str]
    restic_repo_path: str
    restic_warn_hours: float
    restic_critical_hours: float
    restic_integrity_check_enabled: bool
    disk_mounts: list[str]
    disk_warn_pct: float
    disk_critical_pct: float
    # Load
    load_warn_per_cpu: float
    load_critical_per_cpu: float
    # Actions
    auto_fix_min_confidence: str
    actions_timeout_sec: int
    # History
    run_history_last_n_runs: int
    # Knowledge base
    kb_enabled: bool


class SettingsUpdate(BaseModel):
    # All fields optional — only provided fields are updated
    active_target: str | None = None
    llm_enabled: bool | None = None
    llm_model: str | None = None
    llm_max_tokens: int | None = None
    collectors_enabled: list[str] | None = None
    restic_repo_path: str | None = None
    restic_warn_hours: float | None = None
    restic_critical_hours: float | None = None
    restic_integrity_check_enabled: bool | None = None
    disk_mounts: list[str] | None = None
    disk_warn_pct: float | None = None
    disk_critical_pct: float | None = None
    load_warn_per_cpu: float | None = None
    load_critical_per_cpu: float | None = None
    auto_fix_min_confidence: str | None = None
    actions_timeout_sec: int | None = None
    run_history_last_n_runs: int | None = None
    kb_enabled: bool | None = None


@router.get("/settings")
async def get_settings(
    config=Depends(get_config),
) -> SettingsResponse:
    active = config.target
    t = config.targets.get(active)
    available_targets = ["local"] + sorted(k for k in config.targets.keys() if k != "local")
    return SettingsResponse(
        active_target=active,
        available_targets=available_targets,
        target_host=t.host if t else "",
        target_auth=t.auth if t else "local",
        llm_enabled=config.llm.enabled,
        llm_model=config.llm.model,
        llm_max_tokens=config.llm.max_tokens,
        llm_api_key_configured=bool(os.environ.get("ANTHROPIC_API_KEY")),
        collectors_enabled=list(config.collectors.enabled),
        restic_repo_path=config.collectors.restic.repo_path,
        restic_warn_hours=config.rules.restic.warn_hours,
        restic_critical_hours=config.rules.restic.critical_hours,
        restic_integrity_check_enabled=config.collectors.restic.integrity_check_enabled,
        disk_mounts=list(config.collectors.disk.mounts),
        disk_warn_pct=config.rules.disk.warn_pct,
        disk_critical_pct=config.rules.disk.critical_pct,
        load_warn_per_cpu=config.rules.load.warn_per_cpu,
        load_critical_per_cpu=config.rules.load.critical_per_cpu,
        auto_fix_min_confidence=config.actions.auto_fix_min_confidence,
        actions_timeout_sec=config.actions.timeout_sec,
        run_history_last_n_runs=config.run_history.last_n_runs,
        kb_enabled=config.kb.enabled,
    )


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge updates into base dict."""
    result = dict(base)
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


@router.patch("/settings")
async def update_settings(
    body: SettingsUpdate,
    request: Request,
    config=Depends(get_config),
    config_path: Path = Depends(get_config_path),
) -> SettingsResponse:
    """Apply settings changes, persist to YAML, hot-reload app config."""
    # Build nested patch dict from flat SettingsUpdate
    patch: dict[str, Any] = {}

    if body.active_target is not None:
        valid = ["local"] + list(config.targets.keys())
        if body.active_target not in valid:
            raise HTTPException(status_code=422, detail=f"Unknown target '{body.active_target}'. Valid: {valid}")
        patch["target"] = body.active_target

    if body.llm_enabled is not None:
        patch.setdefault("llm", {})["enabled"] = body.llm_enabled
    if body.llm_model is not None:
        patch.setdefault("llm", {})["model"] = body.llm_model
    if body.llm_max_tokens is not None:
        patch.setdefault("llm", {})["max_tokens"] = body.llm_max_tokens

    if body.collectors_enabled is not None:
        unknown = set(body.collectors_enabled) - set(_ALL_COLLECTORS)
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown collectors: {sorted(unknown)}")
        patch.setdefault("collectors", {})["enabled"] = body.collectors_enabled
    if body.restic_repo_path is not None:
        patch.setdefault("collectors", {}).setdefault("restic", {})["repo_path"] = body.restic_repo_path
    if body.restic_integrity_check_enabled is not None:
        patch.setdefault("collectors", {}).setdefault("restic", {})["integrity_check_enabled"] = body.restic_integrity_check_enabled
    if body.disk_mounts is not None:
        patch.setdefault("collectors", {}).setdefault("disk", {})["mounts"] = body.disk_mounts

    if body.restic_warn_hours is not None:
        patch.setdefault("rules", {}).setdefault("restic", {})["warn_hours"] = body.restic_warn_hours
    if body.restic_critical_hours is not None:
        patch.setdefault("rules", {}).setdefault("restic", {})["critical_hours"] = body.restic_critical_hours
    if body.disk_warn_pct is not None:
        patch.setdefault("rules", {}).setdefault("disk", {})["warn_pct"] = body.disk_warn_pct
    if body.disk_critical_pct is not None:
        patch.setdefault("rules", {}).setdefault("disk", {})["critical_pct"] = body.disk_critical_pct
    if body.load_warn_per_cpu is not None:
        patch.setdefault("rules", {}).setdefault("load", {})["warn_per_cpu"] = body.load_warn_per_cpu
    if body.load_critical_per_cpu is not None:
        patch.setdefault("rules", {}).setdefault("load", {})["critical_per_cpu"] = body.load_critical_per_cpu

    if body.auto_fix_min_confidence is not None:
        if body.auto_fix_min_confidence not in _CONFIDENCE_LEVELS:
            raise HTTPException(status_code=422, detail=f"confidence must be one of {_CONFIDENCE_LEVELS}")
        patch.setdefault("actions", {})["auto_fix_min_confidence"] = body.auto_fix_min_confidence

    if body.actions_timeout_sec is not None:
        if body.actions_timeout_sec < 30:
            raise HTTPException(status_code=422, detail="actions_timeout_sec must be >= 30")
        patch.setdefault("actions", {})["timeout_sec"] = body.actions_timeout_sec

    if body.run_history_last_n_runs is not None:
        patch.setdefault("run_history", {})["last_n_runs"] = body.run_history_last_n_runs

    if body.kb_enabled is not None:
        patch.setdefault("kb", {})["enabled"] = body.kb_enabled

    if not patch:
        # Nothing to change — return current settings
        return await get_settings(config)

    # Load raw YAML, merge, validate with Pydantic, write back, hot-reload
    try:
        raw: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
        merged = _deep_merge(raw, patch)

        # Validate via Pydantic before persisting
        from aigis.config import AppConfig
        new_config = AppConfig.model_validate(merged)

        # Write back
        config_path.write_text(yaml.dump(merged, default_flow_style=False, allow_unicode=True))

        # Hot-reload app state
        request.app.state.config = new_config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")

    return await get_settings(new_config)
