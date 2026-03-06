"""Phoenix tracing initialization for LLM observability."""

import io
import os
import sys
import warnings

from aigis.config import AppConfig


def init_tracing(config: AppConfig) -> None:
    """Register Phoenix OTEL tracing if enabled. Must be called before any LLM usage."""
    if not config.llm.phoenix.enabled:
        return

    try:
        from phoenix.otel import register

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            try:
                register(
                    project_name=config.llm.phoenix.project_name,
                    endpoint=config.llm.phoenix.endpoint,
                    auto_instrument=True,
                    verbose=False,
                )
            finally:
                sys.stderr = old_stderr
    except ImportError:
        print(
            "aigis: phoenix tracing enabled but arize-phoenix-otel not installed, skipping",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"aigis: phoenix tracing init failed: {e}", file=sys.stderr)
