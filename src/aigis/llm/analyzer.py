"""Unified LLM analysis: single call for explanation and suggested actions."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

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
    reasoning_trace: str | None = None
    detected_issues: list[dict] | None = None
    manual_recommendations: list[dict] | None = None


def _format_explanation(result: LLMAnalysisResult) -> str:
    """Return just the summary sentence — other fields are stored separately."""
    return result.summary.strip()


def llm_analyze(
    checks: list[CheckResult],
    config: AppConfig,
    previous_run_context: dict | None = None,
    trend_context: dict | None = None,
) -> AnalysisOutput | None:
    """
    Single LLM call: analyze checks, return explanation and suggested actions.
    previous_run_context: optional summary from last run (continuity); see history.build_previous_run_summary.
    trend_context: optional aggregate from last N runs; see history.build_trend_summary.
    Returns None if LLM disabled, no WARN/CRITICAL checks, or API failure.
    """
    if not config.llm.enabled:
        return None
    if not any(c.severity.value in ("WARN", "CRITICAL") for c in checks):
        return None

    # Auto-reingest KB if source files have changed since last ingest
    if config.kb.enabled and config.kb.auto_reingest:
        try:
            from aigis.kb.ingestion import ingest
            from aigis.kb.store import load_store, needs_reingest

            store = load_store(Path(config.kb.store_path).expanduser())
            kb_dir = Path(config.kb.kb_dir).expanduser()
            if kb_dir.exists() and needs_reingest(kb_dir, store):
                ingest(kb_dir, config.kb)
        except Exception as e:
            print(f"aigis kb: auto-reingest failed: {e}", file=sys.stderr)

    # Retrieve relevant KB chunks (graceful: None if disabled / empty / deps missing)
    kb_context: str | None = None
    if config.kb.enabled:
        try:
            from aigis.kb.retrieval import retrieve

            kb_context = retrieve(checks, config.kb)
        except Exception as e:
            print(f"aigis kb: retrieval failed: {e}", file=sys.stderr)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    registry = config.actions.registry
    action_registry = {k: v for k, v in registry.items()} if registry else None

    result = llm_analyze_impl(
        checks=checks,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        api_key=api_key,
        action_registry=action_registry,
        previous_run_context=previous_run_context,
        kb_context=kb_context,
        trend_context=trend_context,
    )
    if not result:
        return None

    explanation = _format_explanation(result)
    allowed_ids = set(config.actions.registry.keys()) if config.actions.registry else set()
    registry_params = {
        aid: list(entry.params) if hasattr(entry, "params") else []
        for aid, entry in (config.actions.registry or {}).items()
    }
    suggested, manual = _map_to_suggested_actions(
        result.recommended_actions,
        allowed_ids,
        registry_params,
    )

    return AnalysisOutput(
        anomaly_explanation=explanation,
        suggested_actions=suggested if suggested else None,
        reasoning_trace=result.reasoning_trace or None,
        detected_issues=result.detected_issues or None,
        manual_recommendations=manual if manual else None,
    )
