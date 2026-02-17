"""Main entry point for the aigis CLI (Facade pattern)."""

import argparse
import sys
from pathlib import Path

from aigis.actions import audit_action, execute_action, get_registry
from aigis.approval import prompt_approval
from aigis.collectors import (
    DiskCollector,
    DockerCollector,
    LoadCollector,
    NetworkCollector,
    ResticCollector,
    run_collectors,
)
from aigis.config import AppConfig, load_config
from aigis.engine import run_rules
from aigis.llm import explain_anomalies, suggest_fixes
from aigis.report import build_report


def _resolve_config(config_path: Path | None) -> AppConfig:
    """Load config from path or default."""
    if config_path and config_path.exists():
        return load_config(config_path)
    return load_config()


def _select_collectors(config: AppConfig) -> list:
    """Select collectors by enabled list (Strategy pattern)."""
    registry = {
        "restic": ResticCollector(),
        "disk": DiskCollector(),
        "load": LoadCollector(),
        "network": NetworkCollector(),
        "docker": DockerCollector(),
    }
    enabled = set(config.collectors.enabled)
    return [registry[k] for k in enabled if k in registry]


def main() -> None:
    """Run the aigis health check pipeline (Collect -> Evaluate -> Report -> [Explain] -> [Suggest] -> [Approve] -> [Execute])."""
    parser = argparse.ArgumentParser(description="AIgis health check")
    parser.add_argument("--config", type=Path, help="Config file path")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Enable suggest fix, human approval, and scripted action",
    )
    args = parser.parse_args()

    config = _resolve_config(args.config)
    collectors = _select_collectors(config)

    # Pipeline: Collect -> Evaluate -> Report
    collector_runs = run_collectors(collectors, config)
    checks = run_rules(collector_runs, config)

    # Optional LLM explanation
    anomaly_explanation = explain_anomalies(checks, config)

    report = build_report(
        checks=checks,
        anomaly_explanation=anomaly_explanation,
    )

    # --fix branch: suggest, approve, execute
    if args.fix and report.overall_severity.value in ("WARN", "CRITICAL"):
        suggested_actions = suggest_fixes(checks, config)
        if suggested_actions:
            report.suggested_actions = suggested_actions

        if suggested_actions and sys.stdin.isatty():
            if prompt_approval(suggested_actions, report):
                registry = get_registry(config)
                for action in suggested_actions:
                    result = execute_action(action, registry, config)
                    audit_action(
                        report.run_id,
                        action,
                        result,
                        config,
                        approved_by="tty",
                    )
                    if not result.success:
                        print(f"Action {action.action_id} failed: {result.stderr}")
            # When not approved, fall through to output report
        # When not TTY, suggested_actions are in report, no approval

    output = report.model_dump_json(indent=2)

    if config.report.output == "stdout":
        print(output)
    elif config.report.file_path:
        Path(config.report.file_path).write_text(output)

    # Exit code: CRITICAL -> 1
    if report.overall_severity.value == "CRITICAL":
        sys.exit(1)


if __name__ == "__main__":
    main()
