---
name: unit-testing
description: 'Write unit tests for pytest-jubilant-bdd reusable Gherkin step handlers. Use when adding, updating, or reviewing unit tests for Given, When, or Then step handlers in the pytest-jubilant-bdd project.'
argument-hint: 'Path to the pytest-jubilant-bdd repository root, or leave blank to use the current directory.'
---

# Write unit tests for pytest-jubilant-bdd

Write unit tests for the reusable Gherkin step handlers defined in `src/pytest_jubilant_bdd/_main.py`. Tests live in `tests/unit/` and follow a consistent pattern: all tests for a handler are grouped under a single test class (`Test<Handler>`). Happy-path tests use `@staticmethod @scenario` with corresponding Gherkin scenarios in `tests/unit/features/`, while error-path tests call handler functions directly with `pytest.raises`.

## Process

1. **Read the step handler** — Identify the handler function in `src/pytest_jubilant_bdd/_main.py`. Note whether it uses `parsers.parse`, `flexible`, or `parsers.re` for pattern matching. If it uses `flexible`, note the optional clauses and any `%...%` blocks.

2. **Read the existing test file** — If a test file exists for the step type (for example, `test_given_steps.py`, `test_when_steps.py`, `test_then_steps.py`), read it to understand the existing patterns, fixtures, and conventions.

3. **Read supporting source** — Understand the handler's dependencies:
   - `_main.py` — `Context` fixture (session-scoped) and all step handlers. Note: `Context` is publicly exported from `pytest_jubilant_bdd`; use `from pytest_jubilant_bdd import Context`.
   - `_context.py` — `Context` object, `ModelMapping`, `stack` class. Know the public API: `context.models`, `context.get_juju()`, `context.get_app()`, `context.wait()`, `context.action_results`, `context.exec_results`.
   - `_parsers.py` — `flexible` parser, `make_list`, `make_dict` converters, `%...%` block syntax.
   - `_assertions.py` — `assertions.app`, `assertions.model`, `assertions.unit` assertion classes.
   - `_constants.py` — `AgentStatus`, `WorkloadStatus`, flag names, status capture group patterns.
    - `errors.py` — Custom exception classes (`AppNotFoundError`, `ModelNotFoundError`, `TooManyDeployedAppsError`, `WaitError`).
   - `tests/unit/helpers.py` — Mock data builders: `make_status_json`, `make_app_with_relation`, `make_app_without_relation`, `make_task_json`.
   - `tests/unit/constants.py` — Path constants only: `REUSABLE_GIVEN_STEP_TESTS`, `REUSABLE_WHEN_STEP_TESTS`, `REUSABLE_THEN_STEP_TESTS`, `MODEL_SUFFIX`.
   - `tests/unit/conftest.py` — Shared fixtures: `mock_subprocess_run`, `mock_status_json`, `_mock_secrets_token_hex`.

4. **Add scenarios to the feature file** — Each `@scenario` test needs a corresponding scenario in `tests/unit/features/<keyword>.feature`. Use a `Background:` section when all scenarios share a common setup step (for example, `Given I add model 'test'`). Name scenarios descriptively.

5. **Write the test functions** — Follow the patterns below.

6. **Run `just unit`** — Verify all tests pass. Run `just fmt` and `just lint` to ensure code style compliance.

## Test file structure

All tests for a handler are grouped under a single test class, typically named `Test<Handler>`. Happy-path tests use `@staticmethod @scenario`; error-path tests are regular instance methods that call the handler directly:

```python
"""Unit tests for reusable *<Keyword>* Gherkin steps."""

from unittest.mock import MagicMock

import pytest
from pytest_bdd import scenario
from jubilant import Task

from constants import (
    MODEL_SUFFIX,
    REUSABLE_<KEYWORD>_STEP_TESTS,
)
from helpers import (
    make_status_json,
    make_app_with_relation,
    make_app_without_relation,
    make_task_json,
)
from pytest_jubilant_bdd import Context

# ruff: noqa[SLF001] — direct handler calls for error-path tests
from pytest_jubilant_bdd._main import (
    <handler functions>,
)

# ``scenario()`` expects a ``str`` path, not a ``Path`` object.
FEATURE_FILE = str(REUSABLE_<KEYWORD>_STEP_TESTS)


# ---
# Fixtures
# ---

# ... autouse fixtures for resetting state, mocking, etc. ...


# ---
# Test classes
# ---


class Test<Handler>:
    """Test the ``<handler>`` *<Keyword>* step handler."""

    @staticmethod
    @scenario(FEATURE_FILE, "Scenario name")
    def test_required(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``<handler>`` with only the required clause."""
        ...

    def test_raises_when_<condition>(
        self, context: Context, mock_subprocess_run: MagicMock
    ) -> None:
        """``<handler>`` raises when ... .

        Notes:
            This error path is tested by calling the handler directly rather
            than via ``@scenario`` because ``@scenario`` runs the Gherkin steps
            before the test body, so exceptions raised during step execution
            cannot be caught with ``pytest.raises`` in the body.
        """
        with pytest.raises(AssertionError, match="..."):
            <handler>(context, ...)
```

**Key rules**:

- `@staicmethod` must be applied to `@scenario` methods inside test classes. It cannot be applied to instance methods.
- All tests (happy and error paths) for a handler should be grouped under a single `Test<Handler>` class.
- Tests that do not use `@scenario` should contain a `Notes` section in the docstring explaining why `@scenario` was not used.

## Key fixtures

### `mock_subprocess_run` (conftest.py)

A function-scoped fixture from `conftest.py` that patches `subprocess.run`. It returns a `MagicMock` with default `stdout` and `stderr` values. Override `mock_subprocess_run.return_value` or `mock_subprocess_run.side_effect` to return custom JSON responses.

### `mock_status_json` (conftest.py)

A function-scoped fixture from `conftest.py` that configures `mock_subprocess_run.return_value` with a default valid `juju status --format json` payload. The default payload contains a single `slurmctld` app with a relation to `slurmd`. Tests that need a different payload should reconfigure `mock_subprocess_run.return_value.stdout` after using this fixture.

### `_mock_secrets_token_hex` (conftest.py)

A session-scoped autouse fixture that mocks `secrets.token_hex` to return `MODEL_SUFFIX` (`"xyz123"`). This ensures model names in unit tests are deterministic.

### `pytest_configure` (conftest.py)

Disables Juju model teardown for all unit tests via `config.option.juju_bdd_no_teardown = True`. Unit tests mock `subprocess.run` and never create real Juju models, so teardown is unnecessary.

### `context` (_main.py)

A session-scoped fixture defined in `_main.py` that provides the `Context` object. Import via `from pytest_jubilant_bdd import Context`. **Important**: the `context` is session-scoped, so models, action results, and exec results persist across tests. Use autouse fixtures to reset state:

```python
@pytest.fixture(autouse=True)
def _reset_stacks(context: Context) -> None:
    """Clear action_results and exec_results before each test."""
    while not context.action_results.is_empty():
        context.action_results.pop()
    while not context.exec_results.is_empty():
        context.exec_results.pop()
```

### `fs` (pyfakefs)

The `fs` fixture from `pyfakefs` provides a `FakeFilesystem`. Use `fs.create_file(path, contents=...)` to create fake files for tests that need to interact with the filesystem (for example, `deploy_local`).

## The `%...%` block syntax in `flexible` parsers

Some `flexible` parser patterns use `%...%` blocks to embed raw regular expressions with named capture groups directly into step patterns. The percent signs are stripped during pattern compilation, and the inner regex is inserted verbatim.

**Step handlers using `%...%` blocks**:

| Handler | `%...%` block |
|---------|--------------|
| `run_action` | `%units? (?P<units>(?:'([^']+)'(?:, (?:and )?\|and )?)+)%` |
| `run_exec` | `%(?P<type_>machines?\|units?) (?P<targets>(?:'([^']+)'(?:, (?:and )?\|and )?)+)%` |
| `assert_all_agent_status` | `%'(?P<status>{'\|'.join(AGENT_STATUSES)})'%` (for `AgentStatus`) and `%(?P<models>...)` for model list |

**Important**: The `_compile` method in `_parsers.py` strips trailing whitespace after `%` blocks to prevent the required regex from demanding a trailing space when a step is used without optional clauses. When writing patterns in `_main.py`, do NOT add trailing spaces after `%` blocks — the parser handles this automatically.

When writing unit tests for handlers with `%...%` blocks, treat the embedded regex as the "required" part of the pattern — test it exactly like required clauses in other `flexible` handlers.

## Testing `flexible` parser handlers

Each step handler that uses the `flexible` parser should have at least two `@scenario` tests:

1. **Required-only** — Exercise only the required clause of the step.
2. **All-optionals** — Exercise the step with every optional clause present.

Do NOT write a separate test for each permutation of optional clauses. The `flexible` parser allows optional clauses to appear in any order, so a single test exercising all optionals is sufficient.

Document this in the test's docstring:

```python
@staticmethod
@scenario(FEATURE_FILE, "Deploy with all optionals")
def test_with_optionals(...) -> None:
    """Test ``deploy`` with all optional clauses.

    Notes:
        The ``flexible`` parser allows optional clauses to appear in any
        order, so a single test exercising all optionals is sufficient.
    """
```

## Testing `parsers.re`-based handlers

Some Then step handlers use `parsers.re` instead of `flexible`. These handlers use raw regular expressions with named capture groups and have no optional clauses. The Then step handlers using `parsers.re` are:

- `assert_workload_status` — Pattern: `the workload status for (?P<type_>app|unit) '(?P<target>[^']+)' is '...'`
- `assert_workload_status_message` — Pattern: `the workload status message for (?P<type_>app|unit) '(?P<target>[^']+)' is '(?P<message>[^']*)'`

Each `parsers.re` handler with a `type_` capture group (app/unit) needs two `@scenario` tests: one for `app` and one for `unit`. These tests exercise different code paths in the handler's `match` statement. The `then.feature` file already contains scenarios for both variants, but the corresponding unit tests have not yet been implemented.

## Testing error paths

Error paths are tested by calling the handler function directly (not via `@scenario`). Use `pytest.raises` to assert the expected exception. Add a `Notes:` section to the docstring explaining why `@scenario` is not used:

```python
def test_raises_when_env_var_missing(
    self, context: Context, monkeypatch: pytest.MonkeyPatch, ...
) -> None:
    """``deploy_local`` raises when ``<APP>_CHARM_PATH`` is not set.

    Notes:
        This error path is tested by calling the handler directly rather
        than via ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises`` in the body.
    """
    monkeypatch.delenv("SLURMCTLD_CHARM_PATH", raising=False)

    with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
        add_unit(context, 3, "slurmctld", "nonexistent")
```

## Testing `juju status`-based handlers

Handlers that call `context.get_app()` or `juju.status()` (for example, `is_integrated`, `is_deployed`, `assert_workload_status`) require mocked `juju status --format json` output. Use the helper functions from `tests/unit/helpers.py`:

- `make_status_json(apps, model_name)` — Builds a full status JSON string.
- `make_app_with_relation(app_name, related_app)` — Returns an app dict with a relation.
- `make_app_without_relation(app_name)` — Returns an app dict with no relations.

Example:

```python
mock_subprocess_run.return_value = MagicMock(
    stdout=make_status_json(
        {"slurmctld": make_app_with_relation("slurmctld", "slurmd")}
    ),
    stderr="",
)
```

For multi-model tests, use `side_effect` to return model-specific JSON:

```python
def _side_effect(*args, **kwargs):
    model_name = "test-xyz123"
    for i, arg in enumerate(args[0]):
        if arg == "--model" and i + 1 < len(args[0]):
            model_name = args[0][i + 1]
            break
    return MagicMock(
        stdout=make_status_json(
            {"slurmctld": make_app_with_relation("slurmctld", "slurmd")},
            model_name=model_name,
        ),
        stderr="",
    )
mock_subprocess_run.side_effect = _side_effect
```

## Testing `Context.wait`-based handlers

Then step handlers use `context.wait()` which polls the `ready` lambda until it returns `True` three times in a row. Mock `time.sleep` as a no-op to avoid real delays. For error paths, mock `time.monotonic` to trigger `TimeoutError`:

```python
@pytest.fixture(autouse=True)
def _mock_time(mocker: MockerFixture) -> None:
    """Mock ``time.sleep`` to avoid real waits."""
    mocker.patch("time.sleep")  # no-op

# In an error-path test:
mocker.patch("time.monotonic", side_effect=[0.0, 999.0, 999.0, 999.0])

with pytest.raises(TimeoutError, match="Wait timed out"):
    assert_workload_status(context, "app", "slurmctld", "active")
```

The `side_effect` list must return `0.0` first (for `start_time`), then values exceeding the timeout for subsequent calls.

## Testing `juju run` / `juju exec`-based handlers

When step handlers call `juju.run()` or `juju.exec()`, mock the `subprocess.run` return value with valid `Task` JSON:

```python
@pytest.fixture(autouse=True)
def _mock_task_json(mock_subprocess_run: MagicMock) -> None:
    """Configure mock_subprocess_run to return valid Task JSON."""
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_task_json("slurmctld/0"),
        stderr="",
    )
```

Use `make_task_json(target, task_id, status, return_code, results)` from `helpers.py` to build the JSON payload.

After the scenario runs, inspect the stack:

```python
assert len(context.action_results) == 1
task = context.action_results.peek()
assert isinstance(task, Task)
assert task.status == "completed"
```

## Asserting subprocess command shapes

Use `mock_subprocess_run.call_args` or `mock_subprocess_run.call_args_list` to verify the exact CLI arguments:

```python
# Single call
assert mock_subprocess_run.call_args[0][0] == [
    "juju", "deploy", "slurmctld",
]

# Multiple calls — filter by command prefix
run_calls = [
    call
    for call in mock_subprocess_run.call_args_list
    if call.args[0] and call.args[0][0:2] == ["juju", "run"]
]
assert len(run_calls) == 3
```

When params files are created dynamically (for example, `juju run --params /tmp/...`), use the last element of the args list as a reference:

```python
assert mock_subprocess_run.call_args[0][0] == [
    "juju",
    "run",
    "--format", "json",
    "slurmctld/0",
    "get-password",
    "--params",
    mock_subprocess_run.call_args[0][0][-1],  # dynamic path
]
```

## Encountering bugs

If you encounter a bug in the production code (`src/pytest_jubilant_bdd/`) while writing unit tests, follow this protocol:

1. **STOP immediately** — Do not make changes to production code without explicit permission.
2. **Propose a resolution** — Describe the bug, its location, the impact on the test(s) you are writing, and your proposed fix. Ask the user:
   - Whether it's okay to proceed with your proposed resolution.
   - Whether you should research further alternatives before acting.
3. **Wait for approval** — Do not edit production code until the user explicitly approves your proposed fix.

This protocol ensures the human-in-the-loop has full visibility into code changes that affect the library's behavior, not just the test suite.

## ModelMapping.__contains__ behavior

The `ModelMapping.__contains__` method raises `ModelNotFoundError` for unknown models rather than returning `False`. If a test for `model_exists` passes a model name that does not exist and does not match the `contains` logic, the error propagates. This is expected behavior — catch both `AssertionError` and `ModelNotFoundError` when testing `model_exists` with a nonexistent model:

```python
with pytest.raises((AssertionError, ModelNotFoundError)):
    model_exists(context, "nonexistent-model")
```

## Constraints

- DO NOT apply `@scenario` to instance methods inside test classes. Use `@staticmethod @scenario` on a static method instead.
- DO NOT use `@scenario` on module-level functions outside of test classes. All tests for a handler should be grouped inside a `Test<Handler>` class.
- DO NOT use `pytest.mark.xfail` for error-path tests. Call the handler directly with `pytest.raises` instead.
- DO NOT interact with the `context` fixture through its private attributes. Use public attributes and methods only.
- DO NOT write a test for every permutation of optional clauses. One test with all optionals is sufficient.
- DO NOT edit production code (`src/pytest_jubilant_bdd/`) without explicit user approval. See "Encountering bugs" above.
- DO NOT silently fix bugs in the codebase. STOP and ask the user before making changes.
- DO use `@scenario` for happy-path tests. It ensures the Gherkin step is correctly parsed and the handler is properly invoked.
- DO use `mock_subprocess_run.call_args` and `mock_subprocess_run.call_args_list` to verify the exact CLI arguments.
- DO use the `stack` public API: `len()`, `peek()`, `is_empty()`, `push()`, `pop()`.
- DO use the `helpers.py` functions (`make_status_json`, `make_app_with_relation`, `make_app_without_relation`, `make_task_json`) for constructing mock data.
- DO use `constants.py` only for path constants and `MODEL_SUFFIX`.
- DO import `Context` from `pytest_jubilant_bdd` (the public package), not from `pytest_jubilant_bdd._context`.
- DO add a `Notes:` section to docstrings explaining any workarounds or design decisions.
- DO use `monkeypatch` for environment variable manipulation.
- DO use `pyfakefs` (`fs` fixture) for filesystem mocking.
- DO group all tests for a handler into a single `Test<Handler>` class (or `Test<Handler>Errors` for error-only classes).
- DO clear session-scoped state (models, stacks) before each test using autouse fixtures.
- DO run `just unit` to verify all tests pass before submitting changes.
- DO run `just fmt` and `just lint` to ensure code style compliance.
