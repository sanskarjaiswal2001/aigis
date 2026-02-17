"""Rule engine (Specification pattern)."""

from aigis.engine.runner import run_rules
from aigis.engine.rules import evaluate_all_rules

__all__ = ["evaluate_all_rules", "run_rules"]
