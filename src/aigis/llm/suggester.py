"""LLM-based fix suggestion. Thin wrapper around llm_analyze."""

from aigis.config import AppConfig
from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult

from aigis.llm.analyzer import llm_analyze


def suggest_fixes(
    checks: list[CheckResult],
    config: AppConfig,
) -> list[SuggestedAction] | None:
    """If LLM enabled and checks have WARN/CRITICAL, request suggested fixes."""
    result = llm_analyze(checks, config)
    return result.suggested_actions if result else None
