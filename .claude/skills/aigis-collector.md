# aigis-collector

Guide for creating a new data collector in the aigis monitoring system.

## Architecture

Collectors follow the **Strategy pattern** via `CollectorProtocol` (defined in `src/aigis/collectors/base.py`).
Each collector gathers system signals and returns a `CollectorRun` containing typed signal models.

## Steps to Add a New Collector

### 1. Define the Signal Schema

Add a new Pydantic model to `src/aigis/schemas/signals.py`:

```python
class MySignal(BaseModel):
    """Description of what this signal captures."""

    model_config = ConfigDict(extra="forbid")

    # typed fields with defaults
    metric_name: str = ""
    metric_value: float = 0.0
```

### 2. Create the Collector Module

Create `src/aigis/collectors/<name>.py`:

```python
"""<Name> collector."""

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, MySignal


class MyCollector:
    """One-line description."""

    collector_id = "<name>"
    # Optional: list commands that must exist on $PATH for local runs
    required_commands: list[str] = ["some-cli"]

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        if runner.is_local:
            return self._collect_local(config)
        return self._collect_remote(config, runner)

    def _collect_local(self, config: AppConfig) -> CollectorRun:
        signals: list[MySignal] = []
        # Use psutil, subprocess, or Python stdlib for local collection
        return CollectorRun(collector_id=self.collector_id, success=True, signals=signals)

    def _collect_remote(self, config: AppConfig, runner) -> CollectorRun:
        r = runner.run(["some-command", "--flag"], timeout=15, login_shell=False)
        if r.returncode != 0:
            return CollectorRun(
                collector_id=self.collector_id,
                success=False,
                error_message=r.stderr or f"exited {r.returncode}",
            )
        signals: list[MySignal] = []
        # Parse r.stdout into signals
        return CollectorRun(collector_id=self.collector_id, success=True, signals=signals)
```

### 3. Register the Collector

**`src/aigis/collectors/__init__.py`** — add import and `__all__` entry:

```python
from aigis.collectors.<name> import MyCollector

__all__ = [
    # ... existing collectors ...
    "MyCollector",
]
```

**`src/aigis/main.py`** — add to the `_select_collectors` registry dict:

```python
registry = {
    # ... existing ...
    "<name>": MyCollector(),
}
```

### 4. Add Config Section

**`src/aigis/config.py`** — add a Pydantic config model if the collector has settings:

```python
class MyCollectorConfig(BaseModel):
    some_setting: str = ""
```

Add the field to `CollectorsConfig` and set a default.

**`config/default.yaml`** — add matching YAML:

```yaml
collectors:
  enabled:
    - <name>  # add to enabled list
  <name>:
    some_setting: ""
```

### 5. Add Rules (optional)

If the collector needs health-check evaluation, add rule predicates in `src/aigis/engine/rules.py` following the specification pattern used by existing rules.

Add thresholds to `config/default.yaml` under `rules:`.

### 6. Write Tests

Add tests in `tests/test_collectors.py` or a new `tests/test_<name>.py`:

- Test local collection with mocked psutil/subprocess
- Test remote collection with a mock runner
- Test error handling (command not found, non-zero exit)
- Test config integration

Run: `uv run pytest tests/test_<name>.py -v`

## Key Files

| File | Purpose |
|------|---------|
| `src/aigis/collectors/base.py` | `CollectorProtocol` + `run_collectors()` |
| `src/aigis/collectors/__init__.py` | Collector registry exports |
| `src/aigis/schemas/signals.py` | Signal Pydantic models |
| `src/aigis/config.py` | Config models |
| `src/aigis/main.py` | `_select_collectors()` wiring |
| `src/aigis/engine/rules.py` | Rule predicates |
| `config/default.yaml` | Default configuration |

## Reference Implementations

- **Simple**: `src/aigis/collectors/disk.py` — psutil local, `df` remote
- **Complex**: `src/aigis/collectors/restic.py` — multi-command, config-heavy
- **Windows**: `src/aigis/collectors/windows_services.py` — platform-specific
