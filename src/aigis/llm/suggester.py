"""LLM-based fix suggestion. Returns structured SuggestedActions only."""

import json
import os

from aigis.config import AppConfig
from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult

from aigis.llm.client import suggest_fixes_impl


def suggest_fixes(
    checks: list[CheckResult],
    config: AppConfig,
) -> list[SuggestedAction] | None:
    """
    If LLM enabled and checks have WARN/CRITICAL, request suggested fixes.
    Validates output against registry (rejects unknown action_id or invalid params).
    Returns list of SuggestedAction or None.
    """
    if not config.llm.enabled:
        return None
    if not any(c.severity.value in ("WARN", "CRITICAL") for c in checks):
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    raw = suggest_fixes_impl(
        checks=checks,
        config=config,
        api_key=api_key,
    )
    if not raw:
        return None

    allowed_ids = set(config.actions.registry.keys())
    result: list[SuggestedAction] = []
    for action in raw:
        if action.action_id not in allowed_ids:
            continue
        # Validate params exist and types
        entry = config.actions.registry.get(action.action_id)
        if entry:
            required = set(entry.params)
            provided = set(action.params.keys())
            if required <= provided or not required:
                result.append(action)
    return result if result else None
