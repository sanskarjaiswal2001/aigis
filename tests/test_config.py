"""Tests for configuration loading and validation."""

import pytest
from pydantic import ValidationError

from aigis.config import (
    AppConfig,
    CollectorsConfig,
    LLMConfig,
    RulesConfig,
    TargetConfig,
    load_config,
)


def test_minimal_config() -> None:
    """AppConfig requires only 'target'."""
    config = AppConfig(target="local")
    assert config.target == "local"
    assert config.targets == {}
    assert config.collectors.enabled == ["restic", "disk", "load", "network", "docker"]


def test_config_with_targets() -> None:
    """AppConfig accepts arbitrary target names via dict."""
    config = AppConfig(
        target="myhost",
        targets={
            "myhost": TargetConfig(host="user@10.0.0.1", auth="key"),
            "another": TargetConfig(host="user@10.0.0.2", auth="password", password="enc"),
        },
    )
    assert "myhost" in config.targets
    assert "another" in config.targets
    assert config.targets["myhost"].auth == "key"
    assert config.targets["another"].auth == "password"


def test_targets_config_not_class() -> None:
    """TargetsConfig class was removed; AppConfig.targets is dict[str, TargetConfig]."""
    import aigis.config as cfg_module

    assert not hasattr(cfg_module, "TargetsConfig")


def test_target_config_extra_forbid() -> None:
    """TargetConfig rejects unknown fields."""
    with pytest.raises(ValidationError):
        TargetConfig.model_validate({"host": "x", "unknown_field": "y"})


def test_config_extra_forbid() -> None:
    """AppConfig rejects unknown top-level fields."""
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"target": "local", "unknown_section": True})


def test_collectors_config_defaults() -> None:
    """CollectorsConfig has sensible defaults."""
    c = CollectorsConfig()
    assert "restic" in c.enabled
    assert c.restic.timeout_sec == 30
    assert c.disk.mounts == []


def test_rules_config_defaults() -> None:
    """RulesConfig has threshold defaults."""
    r = RulesConfig()
    assert r.disk.warn_pct == 85
    assert r.disk.critical_pct == 95
    assert r.memory.warn_pct == 80.0


def test_llm_config_defaults() -> None:
    """LLM config defaults to disabled."""
    llm = LLMConfig()
    assert llm.enabled is False
    assert "claude" in llm.model


def test_load_config_default_path() -> None:
    """load_config loads from default YAML."""
    config = load_config()
    assert config.target is not None


def test_load_config_missing_file() -> None:
    """load_config raises FileNotFoundError for missing path."""
    from pathlib import Path

    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_config_model_copy_immutable() -> None:
    """model_copy returns a new config without mutating the original."""
    original = AppConfig(target="local")
    updated = original.model_copy(update={"target": "remote"})
    assert original.target == "local"
    assert updated.target == "remote"
