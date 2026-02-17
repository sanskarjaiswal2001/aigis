"""Anomaly explainer. LLM used only for explanation, no tools."""

import os

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult

from aigis.llm.client import explain_anomalies_impl


def explain_anomalies(
    checks: list[CheckResult],
    config: AppConfig,
) -> str | None:
    """
    If LLM enabled and checks contain WARN/CRITICAL, request explanation.
    Returns anomaly_explanation string or None.
    """
    if not config.llm.enabled:
        return None
    if not any(c.severity.value in ("WARN", "CRITICAL") for c in checks):
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    return explain_anomalies_impl(
        checks=checks,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        api_key=api_key,
    )
