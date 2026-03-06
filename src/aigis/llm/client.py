"""Anthropic API client with strict output schema."""

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult

from aigis.llm.prompts import AIGIS_SYSTEM_PROMPT


def _sanitize_model(model: str) -> str:
    """Strip provider prefix (e.g. anthropic/) for direct Anthropic API."""
    return re.sub(r"^[a-z]+/", "", model)


def _strip_json_block(text: str) -> str:
    """Remove markdown code block wrapper if present."""
    text = text.strip()
    if text.startswith("```"):
        match = re.match(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return text


def _fix_trailing_comma(s: str) -> str:
    """Remove trailing commas before ] or } to make lenient JSON parseable."""
    return re.sub(r",\s*([}\]])", r"\1", s)


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from text. Tries block first, then finds {...}."""
    text = _strip_json_block(text).strip()
    # Discard leading text before first {
    start = text.find("{")
    if start < 0:
        return None
    text = text[start:]
    # Try parsing (with trailing-comma fix for truncated LLM output)
    for raw in [text, _fix_trailing_comma(text)]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    # Try to find balanced {...} and parse substring
    depth = 0
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                sub = text[: i + 1]
                for raw in [sub, _fix_trailing_comma(sub)]:
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        pass
                break
    return None


@dataclass
class LLMAnalysisResult:
    """Result of unified LLM health analysis."""

    summary: str
    confidence: str
    detected_issues: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    reasoning_trace: str


def _format_checks_for_input(checks: list[CheckResult]) -> str:
    """Format checks as structured JSON for LLM input."""
    data = [
        {
            "check_id": c.check_id,
            "name": c.name,
            "severity": c.severity.value,
            "message": c.message,
            "value": c.value,
            "raw_signal_ref": c.raw_signal_ref,
        }
        for c in checks
    ]
    return json.dumps(data, indent=2)


def llm_analyze_impl(
    checks: list[CheckResult],
    model: str,
    max_tokens: int,
    api_key: str | None,
    action_registry: dict[str, Any] | None = None,
    previous_run_context: dict | None = None,
) -> LLMAnalysisResult | None:
    """
    Call Anthropic API with AIgis system prompt.
    Returns parsed analysis or None on failure.
    """
    if not api_key:
        print("aigis: ANTHROPIC_API_KEY not set, skipping LLM analysis", file=sys.stderr)
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        checks_json = _format_checks_for_input(checks)

        registry_info = ""
        if action_registry:
            registry_info = "\n\nAvailable action registry (action_id -> params):\n"
            for aid, entry in action_registry.items():
                params = getattr(entry, "params", []) if hasattr(entry, "params") else []
                registry_info += f"- {aid}: params {params}\n"

        previous_run_block = ""
        if previous_run_context:
            prev = previous_run_context
            lines = [
                "Previous run (continuity):",
                f"  Run ID: {prev.get('last_run_id', '?')}",
                f"  Timestamp: {prev.get('last_timestamp', '?')}",
                f"  Target: {prev.get('last_target', '?')}",
                f"  Overall severity: {prev.get('last_severity', '?')}",
            ]
            failed = prev.get("last_failed_checks") or []
            if failed:
                lines.append("  Failed/warn checks:")
                for item in failed:
                    lines.append(f"    - {item}")
                msg_map = prev.get("last_failed_check_messages") or {}
                if msg_map:
                    lines.append("  Check messages (for comparison with current run):")
                    for cid, msg in msg_map.items():
                        lines.append(f"    - {cid}: {msg}")
            collectors_failed = prev.get("last_collector_failures") or []
            if collectors_failed:
                lines.append(f"  Collectors that failed: {', '.join(collectors_failed)}")
            suggested = prev.get("last_suggested_action_count", 0) or 0
            healing = prev.get("last_healing_actions") or []
            lines.append(f"  Suggested actions (last run): {suggested}")
            if healing:
                lines.append("  Healing actions executed:")
                for h in healing:
                    lines.append(f"    - {h.get('action_id', '?')}: {'success' if h.get('success') else 'failed'}")
            else:
                lines.append("  Healing actions executed: none")
            lines.append(f"  Any wait-required action was applied: {prev.get('any_wait_required', False)}")
            previous_run_block = (
                "\n\nUse this context: do not suggest the same fix again if it was already applied; "
                "if a wait-required fix was applied and the issue persists, suggest a follow-up or mark for human review; "
                "compare check messages to see if issues are unchanged, improved, or new.\n\n"
                + "\n".join(lines)
                + "\n\n"
            )

        user_content = f"""Analyze the following infrastructure health check results.
{previous_run_block}{registry_info}

Health check results (JSON):
{checks_json}

Respond with strict JSON only, following the OUTPUT FORMAT in your instructions."""

        response = client.messages.create(
            model=_sanitize_model(model),
            max_tokens=max_tokens,
            system=AIGIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text if response.content else ""
        if not text.strip():
            return None

        parsed = _extract_json(text)
        if not parsed or not isinstance(parsed, dict):
            snippet = text[:500].replace("\n", " ")
            print(f"aigis: LLM response could not be parsed as JSON (first 500 chars: {snippet!r}...)", file=sys.stderr)
            return None

        # Accept both "summary" and "explanation" for backwards compatibility
        summary = parsed.get("summary") or parsed.get("explanation") or ""
        return LLMAnalysisResult(
            summary=summary,
            confidence=parsed.get("confidence", "low"),
            detected_issues=parsed.get("detected_issues", []),
            recommended_actions=parsed.get("recommended_actions", []),
            reasoning_trace=parsed.get("reasoning_trace", ""),
        )
    except Exception as e:
        print(f"aigis: LLM analysis failed: {e}", file=sys.stderr)
        return None


def _map_to_suggested_actions(
    recommended_actions: list[dict[str, Any]],
    allowed_ids: set[str],
    registry_params: dict[str, list[str]],
) -> list[SuggestedAction]:
    """Map LLM recommended_actions to SuggestedAction, validating against registry."""
    result: list[SuggestedAction] = []
    for a in recommended_actions:
        action_id = str(a.get("action_id", ""))
        if action_id not in allowed_ids:
            continue
        required = set(registry_params.get(action_id, []))
        params = a.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        # Coerce values to allowed types
        clean_params: dict[str, str | int | float | bool] = {}
        for k, v in params.items():
            if isinstance(v, (str, int, float, bool)):
                clean_params[k] = v
            else:
                clean_params[k] = str(v)
        if required and not (required <= set(clean_params.keys())):
            continue
        result.append(
            SuggestedAction(
                action_id=action_id,
                params=clean_params,
                reason=str(a.get("description", a.get("reason", ""))),
            )
        )
    return result
