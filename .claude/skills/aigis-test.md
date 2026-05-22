# aigis-test

Guide for writing and running tests in the aigis project.

## Framework & Setup

- **pytest 8.0+** via `uv run pytest`
- Test files live in `tests/` at the project root
- Install dev dependencies: `uv pip install -e ".[dev]"`

## Running Tests

```bash
# All tests
uv run pytest

# Verbose with output
uv run pytest -v -s

# Specific file
uv run pytest tests/test_collectors.py -v

# Specific test function
uv run pytest tests/test_collectors.py::test_disk_collector_local -v

# By marker
uv run pytest -m unit
uv run pytest -m integration

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Stop on first failure
uv run pytest -x
```

## Test Organization

```
tests/
├── __init__.py
├── test_actions.py        # Action execution & audit
├── test_collectors.py     # All collectors (local + remote)
├── test_config.py         # Config loading & validation
├── test_engine.py         # Rule evaluation engine
├── test_history.py        # Run history tracking
├── test_llm.py            # LLM analysis (mocked API)
├── test_report.py         # Report building & markdown
├── test_restic.py         # Restic collector (complex)
├── test_runner.py         # Local & SSH runner
└── test_schemas.py        # Pydantic schema validation
```

## Writing Tests

### Test Structure

Use pytest markers for categorization:

```python
import pytest

@pytest.mark.unit
def test_my_feature():
    """Test description."""
    # Arrange
    config = ...

    # Act
    result = my_function(config)

    # Assert
    assert result.success is True
    assert len(result.items) == 3
```

### Testing Collectors

Mock the runner for remote tests, psutil for local:

```python
from unittest.mock import MagicMock, patch
from aigis.collectors.disk import DiskCollector
from aigis.config import load_config


def test_disk_collector_local():
    config = load_config()
    collector = DiskCollector()

    with patch("psutil.disk_partitions") as mock_parts, \
         patch("psutil.disk_usage") as mock_usage:
        mock_parts.return_value = [MagicMock(mountpoint="/", device="/dev/sda1")]
        mock_usage.return_value = MagicMock(percent=45.0, used=50_000_000_000, total=100_000_000_000)

        runner = MagicMock(is_local=True)
        result = collector.collect(config, runner)

    assert result.success is True
    assert len(result.signals) == 1
    assert result.signals[0].used_pct == 45.0


def test_disk_collector_remote():
    config = load_config()
    collector = DiskCollector()

    runner = MagicMock(is_local=False)
    runner.run.return_value = MagicMock(
        returncode=0,
        stdout="Filesystem  1K-blocks  Used  Available  Capacity  Mounted\n/dev/sda1  100000  45000  55000  45%  /\n",
    )

    result = collector.collect(config, runner)
    assert result.success is True
```

### Testing Rules

```python
from aigis.engine import run_rules
from aigis.schemas.signals import CollectorRun, DiskSignal


def test_disk_warning_rule():
    runs = [CollectorRun(
        collector_id="disk",
        success=True,
        signals=[DiskSignal(mount_point="/", used_pct=88.0, used_gb=88, total_gb=100, device="/dev/sda1")],
    )]
    config = load_config()
    checks = run_rules(runs, config)

    disk_checks = [c for c in checks if c.collector_id == "disk"]
    assert any(c.severity.value == "WARN" for c in disk_checks)
```

### Testing LLM (Mocked)

Always mock the Anthropic API client:

```python
from unittest.mock import patch, MagicMock


@patch("aigis.llm.client.anthropic.Anthropic")
def test_llm_analysis(mock_anthropic):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(input={
        "anomaly_explanation": "Test explanation",
        "detected_issues": [],
        "suggested_actions": [],
        "confidence": "high",
    })]
    mock_anthropic.return_value.messages.create.return_value = mock_response
    # ... test llm_analyze()
```

### Testing API Routes

Use FastAPI TestClient:

```python
from fastapi.testclient import TestClient
from aigis.web.app import create_app
from aigis.config import load_config


def test_runs_endpoint():
    config = load_config()
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/runs")
    assert response.status_code == 200
```

## Fixtures

Common fixtures to define in `tests/conftest.py`:

```python
import pytest
from aigis.config import load_config, AppConfig


@pytest.fixture
def config() -> AppConfig:
    return load_config()


@pytest.fixture
def mock_runner():
    from unittest.mock import MagicMock
    runner = MagicMock()
    runner.is_local = True
    return runner
```

## TDD Workflow

1. **RED**: Write the test first — it should fail
2. **GREEN**: Write minimal implementation to pass
3. **REFACTOR**: Clean up, verify coverage
4. Target: **80%+ coverage**

## Key Files

| File | Purpose |
|------|---------|
| `tests/` | All test modules |
| `pyproject.toml` | pytest in `[project.optional-dependencies].dev` |
| `src/aigis/config.py` | `load_config()` used in most test fixtures |

## Existing Test Files Reference

| Test File | Tests For |
|-----------|-----------|
| `test_collectors.py` | Collector local/remote collection |
| `test_engine.py` | Rule evaluation with various signal inputs |
| `test_config.py` | YAML loading, defaults, validation |
| `test_llm.py` | LLM client with mocked Anthropic API |
| `test_history.py` | Run history append/load/trend |
| `test_runner.py` | Local subprocess + SSH runner |
| `test_schemas.py` | Pydantic model validation |
| `test_actions.py` | Action execution + audit logging |
| `test_report.py` | Report building + markdown rendering |
