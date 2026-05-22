"""Tests for LLM module: analyzer, client helpers, and action mapping."""

from unittest.mock import patch, MagicMock

from aigis.config import ActionRegistryEntry, ActionsConfig, AppConfig, LLMConfig
from aigis.llm.analyzer import AnalysisOutput, llm_analyze
from aigis.llm.client import (
    LLMAnalysisResult,
    _extract_json,
    _fix_trailing_comma,
    _format_checks_for_input,
    _map_to_suggested_actions,
    _sanitize_model,
    _strip_json_block,
)
from aigis.schemas.checks import CheckResult, Severity


def _make_config(llm_enabled: bool = True) -> AppConfig:
    return AppConfig(
        target="local",
        llm=LLMConfig(enabled=llm_enabled, model="anthropic/claude-sonnet-4-20250514", max_tokens=512),
        actions=ActionsConfig(
            registry={
                "restart_container": ActionRegistryEntry(script="scripts/actions/restart_container.sh", params=["container_name"]),
                "clear_disk_cache": ActionRegistryEntry(script="scripts/actions/clear_disk_cache.sh", params=[]),
            },
        ),
    )


class TestSanitizeModel:
    def test_strips_prefix(self) -> None:
        assert _sanitize_model("anthropic/claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"

    def test_no_prefix(self) -> None:
        assert _sanitize_model("claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"


class TestStripJsonBlock:
    def test_plain_json(self) -> None:
        assert _strip_json_block('{"a": 1}') == '{"a": 1}'

    def test_code_block(self) -> None:
        assert _strip_json_block('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_code_block_no_lang(self) -> None:
        assert _strip_json_block('```\n{"a": 1}\n```') == '{"a": 1}'


class TestFixTrailingComma:
    def test_removes_trailing_comma_before_brace(self) -> None:
        assert _fix_trailing_comma('{"a": 1,}') == '{"a": 1}'

    def test_removes_trailing_comma_before_bracket(self) -> None:
        assert _fix_trailing_comma('[1, 2,]') == '[1, 2]'

    def test_no_change_when_clean(self) -> None:
        assert _fix_trailing_comma('{"a": 1}') == '{"a": 1}'


class TestExtractJson:
    def test_simple_json(self) -> None:
        result = _extract_json('{"summary": "ok"}')
        assert result == {"summary": "ok"}

    def test_json_in_code_block(self) -> None:
        text = '```json\n{"summary": "ok"}\n```'
        result = _extract_json(text)
        assert result == {"summary": "ok"}

    def test_json_with_leading_text(self) -> None:
        text = 'Here is the analysis:\n{"summary": "ok"}'
        result = _extract_json(text)
        assert result == {"summary": "ok"}

    def test_returns_none_for_no_json(self) -> None:
        assert _extract_json("no json here") is None

    def test_handles_trailing_comma(self) -> None:
        result = _extract_json('{"a": 1,}')
        assert result == {"a": 1}


class TestFormatChecksForInput:
    def test_formats_checks(self) -> None:
        checks = [
            CheckResult(check_id="disk", name="Disk", severity=Severity.WARN, message="85%", value=85.0),
        ]
        output = _format_checks_for_input(checks)
        assert '"check_id": "disk"' in output
        assert '"severity": "WARN"' in output


class TestMapToSuggestedActions:
    def test_matches_registry_actions(self) -> None:
        recommended = [
            {"action_id": "restart_container", "params": {"container_name": "nginx"}, "description": "Restart nginx"},
        ]
        allowed = {"restart_container", "clear_disk_cache"}
        params = {"restart_container": ["container_name"], "clear_disk_cache": []}
        matched, manual = _map_to_suggested_actions(recommended, allowed, params)
        assert len(matched) == 1
        assert matched[0].action_id == "restart_container"
        assert matched[0].params["container_name"] == "nginx"
        assert len(manual) == 0

    def test_unmatched_goes_to_manual(self) -> None:
        recommended = [
            {"action_id": "unknown_action", "description": "Do something manual", "risk_level": "medium"},
        ]
        matched, manual = _map_to_suggested_actions(recommended, set(), {})
        assert len(matched) == 0
        assert len(manual) == 1
        assert manual[0]["description"] == "Do something manual"
        assert manual[0]["risk_level"] == "medium"

    def test_skips_missing_required_params(self) -> None:
        recommended = [
            {"action_id": "restart_container", "params": {}, "description": "No params given"},
        ]
        allowed = {"restart_container"}
        params = {"restart_container": ["container_name"]}
        matched, manual = _map_to_suggested_actions(recommended, allowed, params)
        assert len(matched) == 0

    def test_coerces_param_types(self) -> None:
        recommended = [
            {"action_id": "clear_disk_cache", "params": {}, "description": "Clear cache"},
        ]
        allowed = {"clear_disk_cache"}
        params = {"clear_disk_cache": []}
        matched, _ = _map_to_suggested_actions(recommended, allowed, params)
        assert len(matched) == 1

    def test_manual_includes_steps(self) -> None:
        recommended = [
            {"action_id": "manual_cleanup", "description": "Clean logs", "steps": ["rm /var/log/old", "df -h"]},
        ]
        _, manual = _map_to_suggested_actions(recommended, set(), {})
        assert len(manual) == 1
        assert len(manual[0]["steps"]) == 2


class TestLlmAnalyze:
    """Tests for the llm_analyze facade."""

    def test_returns_none_when_disabled(self) -> None:
        config = _make_config(llm_enabled=False)
        checks = [CheckResult(check_id="x", name="X", severity=Severity.WARN, message="w")]
        assert llm_analyze(checks, config) is None

    def test_returns_none_when_all_ok(self) -> None:
        config = _make_config(llm_enabled=True)
        checks = [CheckResult(check_id="x", name="X", severity=Severity.OK, message="ok")]
        assert llm_analyze(checks, config) is None

    @patch("aigis.llm.analyzer.llm_analyze_impl")
    def test_returns_analysis_on_success(self, mock_impl: MagicMock) -> None:
        mock_impl.return_value = LLMAnalysisResult(
            summary="Disk is filling up",
            confidence="high",
            detected_issues=[{"component": "disk", "severity": "WARN", "explanation": "high usage"}],
            recommended_actions=[
                {"action_id": "clear_disk_cache", "params": {}, "description": "Clear cache"},
            ],
            reasoning_trace="Checked disk thresholds",
        )
        config = _make_config(llm_enabled=True)
        checks = [CheckResult(check_id="disk", name="Disk", severity=Severity.WARN, message="85%")]
        result = llm_analyze(checks, config)
        assert result is not None
        assert isinstance(result, AnalysisOutput)
        assert result.anomaly_explanation == "Disk is filling up"
        assert result.reasoning_trace == "Checked disk thresholds"
        assert result.detected_issues is not None
        assert len(result.detected_issues) == 1
        assert result.suggested_actions is not None
        assert result.suggested_actions[0].action_id == "clear_disk_cache"

    @patch("aigis.llm.analyzer.llm_analyze_impl")
    def test_returns_none_on_api_failure(self, mock_impl: MagicMock) -> None:
        mock_impl.return_value = None
        config = _make_config(llm_enabled=True)
        checks = [CheckResult(check_id="x", name="X", severity=Severity.CRITICAL, message="bad")]
        assert llm_analyze(checks, config) is None

    @patch("aigis.llm.analyzer.llm_analyze_impl")
    def test_separates_manual_recommendations(self, mock_impl: MagicMock) -> None:
        mock_impl.return_value = LLMAnalysisResult(
            summary="Issues found",
            confidence="medium",
            detected_issues=[],
            recommended_actions=[
                {"action_id": "unknown_manual", "description": "Check logs manually", "risk_level": "low"},
            ],
            reasoning_trace="",
        )
        config = _make_config(llm_enabled=True)
        checks = [CheckResult(check_id="x", name="X", severity=Severity.WARN, message="w")]
        result = llm_analyze(checks, config)
        assert result is not None
        assert result.suggested_actions is None  # No registry match
        assert result.manual_recommendations is not None
        assert len(result.manual_recommendations) == 1
        assert result.manual_recommendations[0]["description"] == "Check logs manually"


class TestLlmModuleExports:
    """Verify the cleanup removed legacy exports."""

    def test_no_explain_anomalies(self) -> None:
        import aigis.llm as llm_mod
        assert not hasattr(llm_mod, "explain_anomalies")

    def test_no_suggest_fixes(self) -> None:
        import aigis.llm as llm_mod
        assert not hasattr(llm_mod, "suggest_fixes")

    def test_exports_llm_analyze(self) -> None:
        from aigis.llm import llm_analyze as fn
        assert callable(fn)

    def test_exports_analysis_output(self) -> None:
        from aigis.llm import AnalysisOutput as cls
        assert cls is not None
