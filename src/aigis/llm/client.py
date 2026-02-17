"""Anthropic API client with strict output schema."""

import json

from aigis.schemas.actions import SuggestedAction
from aigis.schemas.checks import CheckResult


def explain_anomalies_impl(
    checks: list[CheckResult],
    model: str,
    max_tokens: int,
    api_key: str | None,
) -> str | None:
    """
    Call Anthropic API with sanitized prompt. Returns explanation or None on failure.
    Uses structured output schema: { "explanation": "string" }.
    """
    if not api_key:
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        check_summary = "\n".join(
            f"- {c.check_id}: {c.severity.value} - {c.message}" for c in checks
        )
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": f"Given these health check results:\n{check_summary}\n\nProvide a brief explanation of what might be wrong and what to check. Respond with JSON only: {{\"explanation\": \"your text\"}}",
                }
            ],
        )
        text = response.content[0].text if response.content else ""
        if text.strip():
            parsed = json.loads(text)
            return parsed.get("explanation")
    except Exception:
        pass
    return None


def suggest_fixes_impl(
    checks: list[CheckResult],
    config,
    api_key: str | None,
) -> list[SuggestedAction] | None:
    """
    Call Anthropic API for suggested fixes. Returns list of SuggestedAction or None.
    Output schema: { "suggested_actions": [ { "action_id": "...", "params": {...}, "reason": "..." } ] }.
    """
    if not api_key:
        return None

    allowed_ids = list(config.actions.registry.keys())
    if not allowed_ids:
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        check_summary = "\n".join(
            f"- {c.check_id}: {c.severity.value} - {c.message}" for c in checks
        )
        prompt = f"""Given these health check results:
{check_summary}

Available actions (use exactly these action_ids): {allowed_ids}
- restart_container: params: {{"container_name": "string"}}
- run_restic_backup: params: {{}}
- clear_disk_cache: params: {{}}

Respond with JSON only:
{{"suggested_actions": [{{"action_id": "...", "params": {{...}}, "reason": "..."}}]}}
"""

        response = client.messages.create(
            model=config.llm.model,
            max_tokens=config.llm.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        if not text.strip():
            return None
        parsed = json.loads(text)
        actions = parsed.get("suggested_actions", [])
        result = []
        for a in actions:
            try:
                result.append(
                    SuggestedAction(
                        action_id=str(a.get("action_id", "")),
                        params=a.get("params", {}),
                        reason=str(a.get("reason", "")),
                    )
                )
            except Exception:
                continue
        return result if result else None
    except Exception:
        return None
