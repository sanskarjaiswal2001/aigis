"""Shared FastAPI dependencies."""

from pathlib import Path

from fastapi import Request

from aigis.config import AppConfig


def get_config(request: Request) -> AppConfig:
    """Retrieve AppConfig from app state (set by create_app)."""
    return request.app.state.config


def get_config_path(request: Request) -> Path:
    """Retrieve the config file path from app state."""
    return request.app.state.config_path


def get_history_path(request: Request) -> Path:
    """Resolve run history JSONL path from config."""
    config: AppConfig = request.app.state.config
    return Path(config.run_history.path).expanduser()


def get_audit_path(request: Request) -> Path:
    """Resolve audit log path from config."""
    config: AppConfig = request.app.state.config
    return Path(config.actions.audit_log_path).expanduser()


def get_reports_dir(request: Request) -> Path:
    """Resolve per-run reports directory (relative to cwd)."""
    return Path(".aigis/reports")
