"""Interactive CLI approval prompt."""

import sys

from aigis.schemas.actions import SuggestedAction
from aigis.schemas.report import HealthReport


def prompt_approval(
    suggested_actions: list[SuggestedAction],
    report: HealthReport,
) -> bool:
    """
    Print report summary and suggested actions, prompt "Apply fix? [y/N]".
    If stdin is not a TTY, return False (no approval when headless).
    """
    if not sys.stdin.isatty():
        return False

    print("\n--- Health Report ---")
    print(f"Overall: {report.overall_severity.value}")
    for c in report.checks:
        if c.severity.value in ("WARN", "CRITICAL"):
            print(f"  {c.check_id}: {c.severity.value} - {c.message}")
    if report.anomaly_explanation:
        print(f"\nExplanation: {report.anomaly_explanation}")

    print("\n--- Suggested Fixes ---")
    for a in suggested_actions:
        print(f"  {a.action_id}: {a.params} - {a.reason}")

    try:
        answer = input("\nApply fix? [y/N]: ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
