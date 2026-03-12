"""Main entry point for the aigis CLI (Facade pattern)."""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

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
from aigis.runner import get_runner
from aigis.history import (
    append_run_history,
    build_previous_run_summary,
    build_run_history_entry,
    build_trend_summary,
    load_run_history,
)
from aigis.llm import llm_analyze
from aigis.llm.tracing import init_tracing
from aigis.report import build_report, render_markdown


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


def _run_server(args: argparse.Namespace) -> None:
    """Start the FastAPI web dashboard."""
    try:
        import uvicorn
        from aigis.web.app import create_app
    except ImportError:
        print(
            "aigis: web dependencies not installed. Run: uv pip install -e '.[web]'",
            file=sys.stderr,
        )
        sys.exit(1)

    config = _resolve_config(getattr(args, "config", None))
    app = create_app(config, config_path=getattr(args, "config", None))
    uvicorn.run(app, host=args.host, port=args.port)


def main() -> None:
    """Run the aigis health check pipeline (Collect -> Evaluate -> Report -> [Explain] -> [Suggest] -> [Approve] -> [Execute])."""
    parser = argparse.ArgumentParser(description="AIgis health check")
    subparsers = parser.add_subparsers(dest="command")

    # "serve" subcommand
    serve_parser = subparsers.add_parser("serve", help="Start the web dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    serve_parser.add_argument("--config", type=Path, help="Config file path")

    # Health check pipeline flags (applied when no subcommand given)
    parser.add_argument("--config", type=Path, help="Config file path")
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Override config target (e.g. 'local' for local-only run)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Enable suggest fix, human approval, and scripted action",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        dest="auto_fix",
        help="Automatically execute actions marked auto_approve=true when LLM confidence >= threshold (for cron/systemd use)",
    )
    parser.add_argument(
        "--generate-key",
        action="store_true",
        help="Generate a new AIGIS_KEY for password encryption and exit",
    )
    parser.add_argument(
        "--encrypt-password",
        type=str,
        metavar="PLAINTEXT",
        help="Encrypt a password for use in config and exit",
    )
    parser.add_argument(
        "--ingest",
        type=Path,
        metavar="PATH",
        help="Ingest a file or directory into the knowledge base and exit",
    )
    args = parser.parse_args()

    # Dispatch subcommands
    if args.command == "serve":
        _run_server(args)
        return

    # Early-exit utility flags
    if args.generate_key:
        from aigis.crypto import generate_key

        key = generate_key()
        print(f"Add this to your .env file:\n\nAIGIS_KEY={key}")
        return

    if args.encrypt_password:
        from aigis.crypto import encrypt_password

        print(encrypt_password(args.encrypt_password))
        return

    if args.ingest:
        config = _resolve_config(args.config)
        from aigis.kb.ingestion import ingest

        result = ingest(args.ingest, config.kb)
        if result.status == "error":
            print(f"Error ingesting {result.source_file}: {result.error_message}", file=sys.stderr)
            sys.exit(1)
        elif result.status == "skipped":
            print(f"Skipped {result.source_file} (already up-to-date)")
        else:
            print(f"Ingested {result.chunks_created} chunks from {result.source_file}")
        return

    config = _resolve_config(args.config)
    if args.target:
        config = config.model_copy(update={"target": args.target})
    init_tracing(config)
    collectors = _select_collectors(config)
    runner = get_runner(config)

    # Load run history for continuity (previous-run context + trend analysis)
    history_entries = load_run_history(config)
    previous_run_context = build_previous_run_summary(history_entries)
    trend_context = build_trend_summary(history_entries)

    started_at = datetime.now()
    t0 = time.perf_counter()

    # Pipeline: Collect -> Evaluate -> Report
    print("AIGIS_PHASE:collection", flush=True)
    collector_runs = run_collectors(collectors, config, runner)
    print("AIGIS_PHASE:evaluation", flush=True)
    checks = run_rules(collector_runs, config)

    # Optional LLM analysis (single call for explanation + suggestions; includes previous-run context + trend)
    if config.llm.enabled:
        print("AIGIS_PHASE:analysis", flush=True)
    llm_result = llm_analyze(checks, config, previous_run_context=previous_run_context, trend_context=trend_context)
    anomaly_explanation = llm_result.anomaly_explanation if llm_result else None
    suggested_actions = llm_result.suggested_actions if llm_result else None

    print("AIGIS_PHASE:reporting", flush=True)
    report = build_report(
        checks=checks,
        collector_runs=collector_runs,
        anomaly_explanation=anomaly_explanation,
        reasoning_trace=llm_result.reasoning_trace if llm_result else None,
        detected_issues=llm_result.detected_issues if llm_result else None,
        manual_recommendations=llm_result.manual_recommendations if llm_result else None,
    )

    # Always attach LLM suggestions so the dashboard can display them.
    if suggested_actions:
        report.suggested_actions = suggested_actions

    # --fix branch: approve and execute suggestions
    healing_results: list[tuple[str, bool]] = []  # (action_id, success) for run history
    if args.fix and report.overall_severity.value in ("WARN", "CRITICAL") and report.suggested_actions:
        if report.suggested_actions and sys.stdin.isatty():
            if prompt_approval(suggested_actions, report):
                registry = get_registry(config)
                for action in suggested_actions:
                    result = execute_action(action, registry, config, runner=runner)
                    healing_results.append((action.action_id, result.success))
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

    # --auto-fix branch: execute auto_approve actions when confidence >= threshold (no TTY required)
    if args.auto_fix and report.overall_severity.value in ("WARN", "CRITICAL") and report.suggested_actions:
        _CONF_ORDER = {"low": 0, "medium": 1, "high": 2}
        min_conf = config.actions.auto_fix_min_confidence
        llm_conf = llm_result.confidence if (llm_result and hasattr(llm_result, "confidence")) else "low"
        confidence_ok = _CONF_ORDER.get(llm_conf, 0) >= _CONF_ORDER.get(min_conf, 1)

        if confidence_ok:
            registry = get_registry(config)
            for action in suggested_actions:
                entry = config.actions.registry.get(action.action_id)
                if entry and entry.auto_approve:
                    result = execute_action(action, registry, config, runner=runner)
                    healing_results.append((action.action_id, result.success))
                    audit_action(report.run_id, action, result, config, approved_by="auto")
                    if not result.success:
                        print(f"Auto-fix: action {action.action_id} failed: {result.stderr}", file=sys.stderr)

    output = json.dumps(
        report.model_dump(mode="json", exclude={"collected_metrics"}, exclude_none=True),
        indent=2,
    )

    if config.report.output == "stdout":
        print(output)
    elif config.report.file_path:
        Path(config.report.file_path).write_text(output)

    md_path = Path(__file__).parent.parent.parent / "report.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")

    # Write per-run report file for web dashboard (full CheckResult detail + LLM analysis)
    reports_dir = Path(".aigis/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{report.run_id}.json").write_text(
        report.model_dump_json(exclude={"collected_metrics"}, exclude_none=True),
        encoding="utf-8",
    )

    print("AIGIS_PHASE:done", flush=True)

    # Append run history for next run's continuity
    suggested_count = len(suggested_actions) if suggested_actions else 0
    history_entry = build_run_history_entry(
        report=report,
        collector_runs=collector_runs,
        checks=checks,
        target=config.target,
        anomaly_explanation=anomaly_explanation,
        suggested_action_count=suggested_count,
        healing_results=healing_results if healing_results else None,
    )
    append_run_history(history_entry, config)

    # Exit code: CRITICAL -> 1
    if report.overall_severity.value == "CRITICAL":
        sys.exit(1)


if __name__ == "__main__":
    main()
