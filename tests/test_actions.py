"""Tests for actions module."""

from aigis.actions import execute_action, get_registry
from aigis.config import load_config
from aigis.schemas.actions import SuggestedAction


def test_registry_resolves_script() -> None:
    """Registry resolves action_id to script path."""
    config = load_config()
    registry = get_registry(config)
    path = registry.get_script_path("restart_container")
    assert path is not None
    assert "restart_container" in str(path)


def test_registry_validates_action() -> None:
    """Registry validates action params."""
    config = load_config()
    registry = get_registry(config)
    valid, _ = registry.validate_action(
        SuggestedAction(action_id="restart_container", params={"container_name": "foo"}, reason="test")
    )
    assert valid


def test_registry_rejects_unknown_action() -> None:
    """Registry rejects unknown action_id."""
    config = load_config()
    registry = get_registry(config)
    valid, err = registry.validate_action(
        SuggestedAction(action_id="unknown_action", params={}, reason="test")
    )
    assert not valid
    assert "Unknown" in err


def test_execute_clear_disk_cache() -> None:
    """Execute clear_disk_cache (no-op script) succeeds."""
    config = load_config()
    registry = get_registry(config)
    action = SuggestedAction(action_id="clear_disk_cache", params={}, reason="test")
    result = execute_action(action, registry, config)
    assert result.success
    assert result.exit_code == 0
