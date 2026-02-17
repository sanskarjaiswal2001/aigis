"""Anomaly explainer. Thin wrapper around llm_analyze."""

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult

from aigis.llm.analyzer import llm_analyze


def explain_anomalies(
    checks: list[CheckResult],
    config: AppConfig,
) -> str | None:
    """If LLM enabled and checks contain WARN/CRITICAL, request explanation."""
    result = llm_analyze(checks, config)
    return result.anomaly_explanation if result else None
