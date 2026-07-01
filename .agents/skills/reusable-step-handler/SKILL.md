---
name: reusable-step-handler
description: 'Write a new reusable Gherkin step handler in `src/pytest_jubilant_bdd/_main.py`, paired with feature scenarios and a unit-test class. Use when adding a Given, When, or Then step handler to the pytest-jubilant-bdd plugin.'
argument-hint: 'Path to the pytest-jubilant-bdd repository root, or leave blank to use the current directory.'
---

# Write a reusable Gherkin step handler

This skill covers implementing a new reusable Gherkin step handler in `src/pytest_jubilant_bdd/_main.py`. It is the implementation counterpart to `.agents/skills/unit-testing/SKILL.md` — **read both before starting**. The unit-testing skill handles `Test<Handler>` class structure, fixtures, error-path conventions, and helper-function usage; this skill covers handler implementation, parser selection, context integration, feature-file authoring, and wiring.

## Process

1. **Pick the parser** — Choose `parsers.parse`, `flexible`, or `parsers.re` for the step pattern.
2. **Write the handler** — Implement the handler function with proper error handling. If it uses `flexible`, follow the rules in. If it needs an embedded regex, use `%…%` blocks.
3. **Wire into `_main.py`** — Place the handler under the correct comment block (Given/When/Then). Ensure it uses `context.get_juju()`and pushes results to the appropriate stack for `when` steps.
4. **Author feature scenarios** — Add a scenario for each happy-path test to `tests/unit/features/<keyword>.feature`.
5. **Write unit tests** — Follow `.agents/skills/unit-testing/SKILL.md`.
6. **Update `README.md`** — Add a bullet for the new public step.
7. **Run `just unit`**, then `just fmt` and `just lint`.

## Overview

All reusable step handlers live in `src/pytest_jubilant_bdd/_main.py`. The module is organized into three sections: **Given** steps (setup and context building), **When** steps (actions), and **Then** steps (attestation and verification). Each handler is decorated with `@given`, `@when`, or `@then` from `pytest_bdd` and accepts a `context: Context` parameter as its first argument.

The handler's step pattern determines which parser to use. Three options exist:

| Parser | How to invoke | When to use |
|--------|--------------|-------------|
| `parsers.parse` | `@given(parsers.parse("I add model '{model}'"))` | Single-line, all required, no reordering |
| `flexible` | `@given(flexible("I deploy '{app}' [in model '{model}']"))` | Optional and/or reorderable clauses |
| `parsers.re` | `@then(parsers.re(r"the workload status for (?P<type_>app\|unit) …"))` | Raw regex; branching on a capture group |

## Decision: which parser to use

### parsers.parse

Use for trivial 1–2 capture steps where every clause is required and the order never changes:

```python
@given(parsers.parse("I add model '{model}'"))
def add_model(context: Context, model: str) -> None:
    ...

@given(parsers.parse("I integrate '{app_one}' with '{app_two}'"))
def integrate(context: Context, app_one: str, app_two: str) -> None:
    ...
```

Do **not** use `parsers.parse` if you need optional clauses, reorderable clauses, or `%…%` blocks.

### flexible

**Default choice for any step with more than one optional parameter.** Square brackets `[…]` mark optional clauses. The `flexible` parser allows those clauses to appear in any order — or not at all.

```python
@given(
    flexible(
        "I deploy '{app}' "
        "[in model '{model}'] "
        "[from channel '{channel}'] "
        "[on base '{base}'] "
        "[with '{num_units}' %units?%]"
    ),
    converters={"num_units": lambda v: int(v) if v is not None else 1},
)
def deploy(context, app, model, channel, base, num_units):
    ...
```

Rules for `flexible` handlers are covered in § 3.

### parsers.re

Use only when the step needs branching on a capture group — that is, when the value of a capture determines which code path the handler takes:

```python
@then(
    parsers.re(
        r"the workload status for (?P<type_>app|unit) '(?P<target>[^']+)' "
        rf"is '{WORKLOAD_STATUS_CAPTURE_GROUP}'"
    )
)
def assert_workload_status(context, type_, target, status):
    match type_:
        case "app":
            ...
        case "unit":
            ...
```

`parsers.re` handlers have no optional clauses and no `%…%` blocks. Every capture group is a named group `(?P<name>…)` in a single raw regex.

## The `flexible` parser — concrete rules

### Optional clauses

Square brackets `[…]` are the **only** way to mark a clause optional. Everything outside brackets is required.

```
"I deploy '{app}' [in model '{model}'] [from channel '{channel}']"
```

Gherkin steps matching this pattern could be:

- `I deploy 'slurmctld'` (required only)
- `I deploy 'slurmctld' in model 'test'`
- `I deploy 'slurmctld' from channel 'latest/edge' in model 'test'`

The order of optional clauses in the Gherkin step does not matter. The parser matches them in any order.

### Converters

`{name}` placeholders always produce strings. Use the `converters` dict to cast them. **Every converter must handle `None`** because optional clauses return `None` for placeholders inside them when the clause is absent:

```python
converters={
    "num_units": lambda v: int(v) if v is not None else 1,
    "path": lambda v: Path(v) if v is not None else v,
    "units": make_list,
    "params": make_dict,
}
```

Built-in converters in `_parsers.py`:

- `make_list` — parses `'a', 'b', and 'c'` into `['a', 'b', 'c']`. Returns `[]` for `None`.
- `make_dict` — parses `k=v k2=v2` into `{'k': 'v', 'k2': 'v2'}`. Returns `{}` for `None`.

### Testing implications

Because optional clauses can appear in any order, a **single "all optionals" test is sufficient** — do not write a test for every permutation. Document this in the test's `Notes:` block.

## The `%…%` block syntax

### What it does

`%…%` embeds a raw regular expression fragment verbatim into the compiled step pattern. The percent signs are stripped by `_STRIP_PERCENT_SIGN_REGEX` in `_parsers.py`; everything between them is inserted as-is into the final regex.

### When to use it

Use `%…%` when a clause needs regex features that `{name}` placeholders cannot express:

- **Quantifiers** on the parenthesized pattern (e.g. `(?:…)+`).
- **Alternation** inside a capture group (e.g. `machines?|units?`).
- **Enum-like capture** from a constant (e.g. `{'|'.join(AGENT_STATUSES)}`).

### Contrast with `{name}` placeholders

| Syntax | Compiles to |
|--------|------------|
| `{name}` | `(?P<name>[^']+)` — captures anything between single quotes |
| `%…%` | Raw regex — you control the capture group shape entirely |

A `{name}` placeholder automatically wraps the capture in `[^']+`. A `%…%` block gives you full control: you can match multi-word targets, repeated patterns, alternation, and more.

### Naming rule

Capture-group names inside `%…%` must match the function-parameter names exactly:

```python
# Pattern:
r"%units? (?P<units>(?:'([^']+)'(?:, (?:and )?|and )?)+)%"

# Handler parameter must be named "units":
def run_action(context, action, units: list[str], params, model):
    ...
```

### Trailing-whitespace gotcha

The `_compile` method in `_parsers.py` strips trailing whitespace after `%…%` blocks so the required regex doesn't demand a trailing space when the step is used without optional clauses. **Never add a space after a `%…%` block in the pattern.**

Do this:

```
r"all agents are %'(?P<status>{'|'.join(AGENT_STATUSES)})'%"
```

Not this:

```
r"all agents are %'(?P<status>{'|'.join(AGENT_STATUSES)})'% "   # WRONG
```

### Existing call-sites

Read these in `_main.py` as canonical examples:

- `run_action` — `%units? (?P<units>(?:'([^']+)'(?:, (?:and )?|and )?)+)%` — optional-units list with Oxford-comma support.
- `run_exec` — `%(?P<type_>machines?|units?) (?P<targets>(?:'([^']+)'(?:, (?:and )?|and )?)+)%` — unit/machine alternation + targets list.
- `assert_all_agent_status` — `%'(?P<status>{'|'.join(AGENT_STATUSES)})'%` — enum-backed capture generated from `AGENT_STATUSES` constant, paired with `%(?P<models>…)` for a models list.

## Base-function / private-helper pattern

When two handlers share most of their CLI call, factor out a private helper. The `deploy` and `deploy_local` handlers both delegate to `_deploy`:

```python
@given(flexible("I deploy '{app}' [in model '{model}'] …"))
def deploy(context, app, model, channel, base, num_units):
    _deploy(context, app, model=model, channel=channel, base=base,
            num_units=num_units)

@given(flexible("I deploy '{app}' from a local charm [located at '{path}'] …"))
def deploy_local(context, app, path, model, base, num_units):
    ...
    _deploy(context, path.resolve(), app, model=model, base=base,
            num_units=num_units)

def _deploy(
    context: Context,
    /,
    charm: str | Path,
    app: str | None = None,
    *,
    model: str | None = None,
    channel: str | None = None,
    base: str | None = None,
    num_units: int = 1,
) -> None:
    juju = context.get_juju(model)
    juju.deploy(charm, app, base=base, channel=channel, num_units=num_units)
```

Rules for private helpers:

- Use positional-only `/` for the first arg and keyword-only `*` after.
- Default values belong on the helper, not on every caller.
- Name the helper with a leading underscore (`_deploy`).
- Do not decorate the helper — only the public handler gets `@given`/`@when`/`@then`.

## Error classes

Use the appropriate error class for each failure mode. All custom errors live in `src/pytest_jubilant_bdd/errors.py`.
ASK FIRST if adding a 

| Error class | When to raise |
|------------|--------------|
| `CharmNotFoundError` | Missing `*.charm` file or unset `<APP>_CHARM_PATH` env var |
| `AppNotFoundError` | `context.get_app()` failed; app not in `juju status` |
| `ModelNotFoundError` | Model name not in `context.models` |
| `TooManyDeployedAppsError` | Multiple apps with the same name; tell user to scope by model |
| `AssertionError` (built-in) | Verification-style Given steps (`is_deployed`, `is_integrated`, `model_exists`) |

When wrapping a `KeyError` or `OSError`, use `raise … from None` to keep the traceback readable:

```python
try:
    path = Path(os.environ[env_var])
except KeyError:
    raise CharmNotFoundError(
        f"Charm not found: environment variable '{env_var}' is not set. "
        f"Either set the environment variable '{env_var}' to the path of "
        f"the local '*.charm' file, or provide a path in the Gherkin step …"
    ) from None
```

Do **not** bury error handling in one-liners or ternary expressions:

```python
# Good: explicit
if path is None:
    env_var = app.upper().replace("-", "_") + "_CHARM_PATH"
    try:
        path = Path(os.environ[env_var])
    except KeyError:
        raise CharmNotFoundError(...) from None

# Bad: buried
path = Path(os.environ[env_var]) if env_var in os.environ else None
```

When converting library errors to `AssertionError` (for Given verification steps), include a helpful message:

```python
try:
    context.get_app(app, model=model)
except AppNotFoundError:
    raise AssertionError(f"'{app}' is not deployed")
except TooManyDeployedAppsError:
    raise AssertionError(
        f"More than one app is named '{app}'. Provide the model name …"
    )
```

## Fixture / context integration

### Accessing Juju

Use `context.get_juju(model)` to obtain a per-model `jubilant.Juju` instance. It creates one on first access and caches it. **Never** construct `Juju()` directly — the context manages model tracking:

```python
juju = context.get_juju(model)   # model-aware
juju = context.get_juju()        # default (current) model
```

### Accessing application state

`context.get_app(app, model=…)` reads `juju status` and returns an `App` dataclass. It raises:

- `AppNotFoundError` — app not found.
- `TooManyDeployedAppsError` — ambiguous app name (same name in multiple models).

For Given verification steps (`is_deployed` pattern), catch these and convert to `AssertionError` with a user-friendly message (§ 6).

### Pushing action/exec results

For `when` steps that call `juju.run()` or `juju.exec()`, push the resulting `Task` onto the context's result stacks so downstream `then` steps can inspect them:

```python
result = juju.run(unit, action, params=params if params else None)
context.action_results.push(result)
```

```python
result = juju.exec(command, **{type_.rstrip("s"): target})
context.exec_results.push(result)
```

Use the `stack` public API: `push()`, `pop()`, `peek()`, `is_empty()`, `len()`.

### Session-scoped state

The `context` fixture is session-scoped. If your handler introduces new mutable state, it will persist across tests. Document it so the unit-test author can clear it in an autouse fixture:

```python
@pytest.fixture(autouse=True)
def _reset_stacks(context: Context) -> None:
    while not context.action_results.is_empty():
        context.action_results.pop()
```

### Then-step polling with `context.wait()`

Then-step handlers use `context.wait()` to poll a readiness condition until the assertion passes three times consecutively:

```python
@then(parsers.re(r"the workload status for (?P<type_>app|unit) …"))
def assert_workload_status(context, type_, target, status):
    match type_:
        case "app":
            context.wait(
                ready=lambda ctx: assertions.app.all_unit_statuses_are(
                    ctx, target, expected=status
                )
            )
        case "unit":
            context.wait(
                ready=lambda ctx: assertions.unit.all_statuses_are(
                    ctx, target, expected=status
                )
            )
```

Key details:

- The `ready` lambda receives the `Context` object — use the `ctx` parameter, not the outer `context`.
- `wait` polls the lambda until it returns `True` three times in a row, then returns.
- On timeout, `wait` raises `TimeoutError` ("Wait timed out") — do **not** catch this; let pytest surface it.
- Assertion helpers live in `src/pytest_jubilant_bdd/_assertions.py`. The three namespaces are `assertions.app`, `assertions.model`, and `assertions.unit`.

Reference handlers: `assert_workload_status`, `assert_workload_status_message`, `assert_all_agent_status`.

## Feature file authoring

Feature files live in `tests/unit/features/<keyword>.feature` (one per step type: `given.feature`, `when.feature`, `then.feature`).

### Scenario naming

Each `@scenario` test method references a scenario by name. Match the existing naming convention:

| Scenario name | Test method |
|--------------|------------|
| `Deploy` | `test_required` |
| `Deploy with all optionals` | `test_with_optionals` |
| `Add unit` | `test_required` |
| `Add unit in model` | `test_with_optionals` |

### Background vs. explicit Given steps

Use a `Background:` block only when **every** scenario in the file shares the same setup step. Otherwise, repeat `Given …` per scenario. The existing `given.feature` file does not use `Background:` — each scenario is self-contained:

```gherkin
Scenario: Deploy
  Given I deploy 'slurmctld'

Scenario: Deploy with all optionals
  Given I add model 'test'
  Given I deploy 'slurmctld' in model 'test' from channel 'latest/edge' on base 'ubuntu@24.04' with '3' units
```

### "All optionals" scenario

Exercise every optional clause in a single scenario. Order them for readability; the `flexible` parser matches them in any order. Do **not** write a separate scenario for each optional clause or for each permutation of clauses.

### New scenarios for `parsers.re` handlers

Handlers using `parsers.re` with a `type_` capture group (e.g. `assert_workload_status`) need **two** scenarios: one for `app` and one for `unit`. These exercise different code paths in the handler's `match` statement.

## Cross-reference: unit tests

Do not duplicate test patterns here. After implementing the handler and feature scenarios, follow the unit-testing skill for writing the test class:

- Path: `.agents/skills/unit-testing/SKILL.md`
- Covers: `Test<Handler>` class structure, `@staticmethod @scenario`, error-path `pytest.raises`, fixture setup (`mock_subprocess_run`, `mock_status_json`, `_mock_time`), helper-function usage (`make_status_json`, `make_app_with_relation`, `make_task_json`), and subprocess assertion patterns.
- **The handler and its tests must land in the same change.**

## Updating `README.md`

If the handler is a public-facing Gherkin step, add a bullet under the appropriate section in `README.md` with a one-line description:

```markdown
* `add_unit`: A `given` step handler for adding units to a deployed
  application.
```

Rules:

- Keep bullets alphabetized within each section (Given / When / Then).
- Use backticks for the handler function name.
- Skip this step for internal helpers (`_deploy`) that aren't surfaced to Gherkin users.

## Constraints

- DO NOT edit production code (`src/pytest_jubilant_bdd/`) without explicit user approval. If you encounter a bug while writing tests, stop and propose a resolution. Wait for approval before making changes.
- DO NOT edit modules other than `src/pytest_jubilant_bdd/_main.py` without explicit user approval. If you want to modify other modules, stop and provide a justification. Wait for approval before making changes.
- DO NOT add new runtime or test dependencies beyond what is already in `pyproject.toml`. The existing test-time dependencies are `jubilant`, `pytest-bdd`, and `pyfakefs`.
- DO add a PEP 257 docstring to every public handler function.
- DO run `just unit` to verify all tests pass after implementing the handler and tests.
- DO run `just fmt` and `just lint` to ensure code style compliance.
- DO use explicit `raise` statements instead of burying error handling in one-liners or ternary expressions.