"""Action registry: maps action_id to script path and param schema."""

from pathlib import Path

from aigis.config import AppConfig
from aigis.schemas.actions import SuggestedAction


class ActionRegistry:
    """Resolves action_id to script path and validates params."""

    def __init__(self, config: AppConfig, project_root: Path | None = None) -> None:
        self._config = config
        self._root = project_root or Path(__file__).parent.parent.parent.parent

    def get_script_path(self, action_id: str) -> Path | None:
        """Resolve action_id to absolute script path. Returns None if not in registry."""
        entry = self._config.actions.registry.get(action_id)
        if not entry:
            return None
        path = Path(entry.script)
        if not path.is_absolute():
            path = self._root / path
        return path

    def get_param_names(self, action_id: str) -> list[str]:
        """Get allowed param names for action_id."""
        entry = self._config.actions.registry.get(action_id)
        if not entry:
            return []
        return list(entry.params)

    def validate_action(self, action: SuggestedAction) -> tuple[bool, str]:
        """
        Validate action against registry. Returns (valid, error_message).
        """
        script_path = self.get_script_path(action.action_id)
        if script_path is None:
            return False, f"Unknown action_id: {action.action_id}"
        if not script_path.exists():
            return False, f"Script not found: {script_path}"
        allowed_params = set(self.get_param_names(action.action_id))
        extra = set(action.params.keys()) - allowed_params
        if extra:
            return False, f"Invalid params: {extra}"
        missing = allowed_params - set(action.params.keys())
        if missing:
            return False, f"Missing required params: {missing}"
        return True, ""


def get_registry(config: AppConfig) -> ActionRegistry:
    """Create ActionRegistry from config."""
    return ActionRegistry(config)
