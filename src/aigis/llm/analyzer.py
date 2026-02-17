"""Unified LLM analysis: single call for explanation and suggested actions."""

import os
from dataclasses import dataclass

from aigis.config import AppConfig
from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult

from aigis.llm.client import (
    LLMAnalysisResult,
    _map_to_suggested_actions,
    llm_analyze_impl,
)


@dataclass
class AnalysisOutput:
    """Output of unified LLM analysis."""

    anomaly_explanation: str | None
    suggested_actions: list[SuggestedAction] | None


def _format_explanation(result: LLMAnalysisResult) -> str:
    """Format LLM analysis result as anomaly explanation string."""
    parts = [result.summary]
    if result.reasoning_trace:
        parts.append(f"\n\nReasoning: {result.reasoning_trace}")
    if result.detected_issues:
        lines = ["\n\nDetected issues:"]
        for d in result.detected_issues:
            comp = d.get("component", "unknown")
            sev = d.get("severity", "")
            expl = d.get("explanation", "")
            lines.append(f"- {comp} ({sev}): {expl}")
        parts.append("\n".join(lines))
    return "".join(parts).strip()


def llm_analyze(
    checks: list[CheckResult],
    config: AppConfig,
) -> AnalysisOutput | None:
    """
    Single LLM call: analyze checks, return explanation and suggested actions.
    Returns None if LLM disabled, no WARN/CRITICAL checks, or API failure.
    """
    if not config.llm.enabled:
        return None
    if not any(c.severity.value in ("WARN", "CRITICAL") for c in checks):
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    registry = config.actions.registry
    action_registry = {k: v for k, v in registry.items()} if registry else None

    result = llm_analyze_impl(
        checks=checks,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        api_key=api_key,
        action_registry=action_registry,
    )
    if not result:
        return None

    explanation = _format_explanation(result)
    allowed_ids = set(config.actions.registry.keys()) if config.actions.registry else set()
    registry_params = {
        aid: list(entry.params) if hasattr(entry, "params") else []
        for aid, entry in (config.actions.registry or {}).items()
    }
    suggested = _map_to_suggested_actions(
        result.recommended_actions,
        allowed_ids,
        registry_params,
    )

    return AnalysisOutput(
        anomaly_explanation=explanation,
        suggested_actions=suggested if suggested else None,
    )
