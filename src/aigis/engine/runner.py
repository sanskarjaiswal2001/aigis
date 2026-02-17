"""Rule engine runner. Wraps rules with error handling."""

from aigis.config import AppConfig
from aigis.schemas.checks import CheckResult, Severity
from aigis.schemas.signals import CollectorRun

from aigis.engine.rules import evaluate_all_rules


def run_rules(
    collector_runs: list[CollectorRun],
    config: AppConfig,
) -> list[CheckResult]:
    """
    Run rules over collector runs. On rule failure, emit CRITICAL CheckResult.
    """
    results: list[CheckResult] = []
    try:
        results = evaluate_all_rules(collector_runs, config)
    except Exception as exc:
        results.append(
            CheckResult(
                check_id="rule_engine",
                name="Rule engine",
                severity=Severity.CRITICAL,
                message=f"Rule engine failed: {exc}",
            )
        )
    return results
