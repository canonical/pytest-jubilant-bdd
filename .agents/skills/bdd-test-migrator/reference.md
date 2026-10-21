# bdd-test-migrator reference

Complete reference for migrating existing `jubilant` integration tests to BDD
with `gherkinator` and `pytest-jubilant-bdd`. Sections shared with greenfield
authoring are identical to the `bdd-test-author` skill; migration-specific
sections cover the jubilant → YAML → BDD pattern mapping, the migration
fidelity checklist, opt-in test gating, and troubleshooting.

## Directory layout

```
tests/integration/
├── assets/                  # Test fixtures (cloud-init files, configs, etc.)
├── features/                # Generated .feature files — committed, kept in sync via gherkinator diff
│   └── functional_edge_tests.feature
├── plans/                   # YAML test plans — the single source of truth
│   ├── edge.yaml
│   ├── beta.yaml            # (as needed)
│   └── ...
├── constants.py             # Feature globs + app names
├── test_edge.py             # scenarios() loader + custom steps, one per risk
├── test_beta.py             # (as needed)
├── mod.just                 # gherkinator subcommands (generate / diff / validate)
└── test_charm.py            # LEGACY jubilant tests — retained until the suite is green
```

Legacy `test_*.py` jubilant tests are **not** deleted during migration — they
stay in place until the whole BDD suite is green, then they are removed.

## YAML test plan schema

Each YAML document maps to one test plan. Multiple documents may live in a
single file, separated by `---`. One file per risk level is the convention.

### Required fields

| Field | Type | Allowed values |
|-------|------|----------------|
| `feature` | string | Human-readable feature name; derives the output filename (`"Functional edge tests"` → `functional_edge_tests.feature`) |
| `type` | string | `functional`, `solution`, `performance`, `reliability`, `security` |
| `status` | string | `planned`, `implemented`, `deprecated` |
| `risk` | string | `edge`, `beta`, `candidate`, `stable` |
| `scenarios` | []string | At least one. First line = scenario title; subsequent lines = Gherkin steps |

Author new plans with `status: implemented`. The `planned` and
`deprecated` statuses are set only at the human's explicit direction —
`pytest-gherkinator` skips those scenarios at runtime (see § pytest-gherkinator
execution ordering).

### Optional fields

| Field | Type | Meaning |
|-------|------|---------|
| `description` | string | Free-form description rendered under `Feature:` |
| `issues` | string | Link to tracked issues (documentation only) |
| `docs` | string | Link to documentation (documentation only) |
| `background` | string | Gherkin steps that run before every scenario |
| `examples` | [][]string | Parametrised data rows; use `<param>` tokens in scenario steps |

### Choosing `type` and `risk`

| `type` | Use for |
|--------|---------|
| `functional` | Typical charm behavior (deploy, integrate, config, actions) |
| `reliability` | HA, multi-unit, scale-up/scale-down |
| `performance` | Benchmarks, throughput |
| `security` | Access control, credentials, secrets handling |
| `solution` | End-to-end user workflows spanning multiple charms |

| `risk` | Use for |
|--------|---------|
| `edge` | Fast core-path tests gating every PR |
| `beta` | Broader coverage, less critical paths |
| `candidate` | Pre-release validation |
| `stable` | Full regression for stable releases |

### Generated Gherkin shape

`gherkinator generate --format gh` renders each plan document as one
`.feature` file, named after the `feature` field (lowercased and
underscored):

- `feature` → the `Feature: <feature>` line (and the output filename).
- `type`, `status`, `risk` → the tag line, in that order:
  `@<type> @<status> @<risk>` (for example `@functional @implemented @edge`).
- `description` → free-form text rendered under `Feature:`.
- `background` → a `Background:` block that runs before every scenario in
  the feature.
- `scenarios` → one `Scenario: <title>` per entry (first line = title;
  subsequent lines = Given/When/Then steps).
- `examples` → when present, the corresponding scenario becomes a
  `Scenario Outline:` with an `Examples:` table; column headers derive from
  the `<param>` tokens in the scenario steps.

The generated Gherkin is validated against the official Cucumber Gherkin
parser; malformed output is rejected at generation time.

## Built-in step phrasing table

Single quotes are required. `[...]` marks optional, reorderable clauses,
`[a|b]` marks a required alternation, and a trailing `[s]` marks an optional
plural. Phrasings omit the leading `Given`/`When`/`Then` keyword — the
section grouping and the **Stanzas** column show which keywords each
handler is registered under.

### Given (setup and state building)

| Step phrasing | Handler | Stanzas |
|---------------|---------|---------|
| `I add model '{model}'` | `add_model` | Given |
| `I add '{n}' unit[s] to app '{app}' [in model '{model}']` | `add_unit` | Given, When |
| `I add [a|'{n}'] machine[s] [to '{target}'] [(that )?use[s] base '{base}'] [with constraints '{constraints}'] [with disks '{disks}'] [in model '{model}']` | `add_machine` | Given |
| `I add storage '{storage}' to unit '{unit}' [from pool '{pool}'] [of size '{size}'] [with '{count}' instance[s]] [in model '{model}']` | `add_storage` | Given |
| `I [forcibly] remove app[s] '{apps}' [destroy its|their storage] [in model '{model}']` | `remove_app` | Given, When |
| `I remove unit[s] '{units}' [in model '{model}']` | `remove_unit` | Given, When |
| `I remove storage '{storages}' [in model '{model}']` | `remove_storage` | Given |
| `I pack [a|an] '{app}' charm [from project directory '{dir}']` | `pack_charm` | Given |
| `I deploy '{app}' [from channel '{channel}'] [on base '{base}'] [to machine[s] '{machines}'] [with '{n}' unit[s]] [with name '{name}'] [with config '{config}'] [with constraint[s] '{constraints}'] [with storage[s] '{storage}'] [in model '{model}']` | `deploy` | Given |
| `I deploy '{app}' from a local charm [located at '{path}'] [on base '{base}'] [to machine[s] '{machines}'] [with '{n}' unit[s]] [with name '{name}'] [with config '{config}'] [with constraint[s] '{constraints}'] [with storage[s] '{storage}'] [in model '{model}']` | `deploy_local` | Given |
| `I create offer '{name}' from app '{app}' and endpoint '{endpoint}' [in model '{model}']` | `create_offer` | Given |
| `I consume offer '{offer}' [as '{alias}'] [in model '{model}']` | `consume_offer` | Given |
| `I integrate '{app_one}' with '{app_two}' [in model '{model}']` | `integrate` | Given, When |
| `I disintegrate '{app_one}' and '{app_two}' [in model '{model}']` | `disintegrate` | Given, When |
| `model '{model}' exists` | `model_exists` | Given |
| `'{option}' for app '{app}' is set to '{value}' [in model '{model}']` | `is_app_config_set` | Given |
| `'{app_one}' is integrated with '{app_two}' [in model '{model}']` | `is_integrated` | Given |
| `'{app}' is deployed [in model '{model}']` | `is_deployed` | Given |
| `application '{app}' exists [in model '{model}']` | `app_exists` | Given |
| `unit '{unit}' exists [in model '{model}']` | `unit_exists` | Given |
| `I reset '{option}' for app '{app}' [in model '{model}']` | `reset_app_config` | Given |
| `I set '{option}' for app '{app}' to '{value}' [in model '{model}']` | `set_app_config` | Given |
| `I set '{option}' for model '{model}' to '{value}'` | `set_model_config` | Given |
| `I reset '{option}' for model '{model}'` | `reset_model_config` | Given |
| `I switch to model '{model}'` | `switch_model` | Given |

### When (actions)

| Step phrasing | Handler | Result stack |
|----------------|---------|--------------|
| `I run action '{action}' on unit[s] '{u1}', '{u2}', and '{u3}' [with parameters '{k=v ...}'] [in model '{model}']` | `run_action` | `context.action_results` |
| `I execute '{command}' on machine[s] '{m1}' and '{m2}' [in model '{model}']` | `run_exec` | `context.exec_results` |
| `I execute '{command}' on unit[s] '{u1}' and '{u2}' [in model '{model}']` | `run_exec` | `context.exec_results` |
| `I ssh into machine '{m}' and I execute '{command}' [in model '{model}']` | `run_ssh` | `context.ssh_results` |
| `I ssh into unit '{u}' and I execute '{command}' [in model '{model}']` | `run_ssh` | `context.ssh_results` |
| `I copy '{source}' to unit '{unit}' [at '{remote_path}'] [in model '{model}']` | `scp_to_unit` | — |
| `I copy '{remote_path}' from unit '{unit}' [to '{local_path}'] [in model '{model}']` | `scp_from_unit` | — |

### Checkpoints (attestation)

Every checkpoint handler is registered for `Given`, `When`, and `Then`
alike, so checkpoints can be used in any stanza through the `And`/`But`
conjunctions.

| Step phrasing | Handler | Status values |
|----------------|---------|---------------|
| `all agents are '{status}' [in model[s] '{m1}', '{m2}', and '{m3}'] [within '{timeout}' seconds]` | `assert_all_agent_status` | `allocating`, `executing`, `error`, `idle`, `lost` |
| `the workload status for app '{app}' is '{status}' [within '{timeout}' seconds]` | `assert_workload_status` | `active`, `blocked`, `error`, `maintenance`, `waiting` |
| `the workload status for unit '{unit}' is '{status}' [within '{timeout}' seconds]` | `assert_workload_status` | (same) |
| `the workload status message for app '{app}' is '{message}' [within '{timeout}' seconds]` | `assert_workload_status_message` | — |
| `the workload status message for unit '{unit}' is '{message}' [within '{timeout}' seconds]` | `assert_workload_status_message` | — |
| `'{count}' instances of storage '{storage}' are attached to unit '{unit}' [in model '{model}'] [within '{timeout}' seconds]` | `assert_storage_attached` | — |
| `I wait for '{wait}' seconds` | `wait_for` | — |

Notes:

- Status values are fixed by the framework. Never invent new ones. The
  optional `within '{timeout}' seconds` clause overrides the global
  `--juju-bdd-wait-timeout` (default 180s) for that single step.
- `with config '{config}'`, `with parameters '{params}'`, and
  `with constraints '{constraints}'` clauses are space-separated `k=v`
  pairs (for example `'mode=fast debug=true'`); lowercase `true`/`false`
  are cast to Python booleans.
- `with storage '{storage}'` clauses are space-separated storage
  directives of the form `name=directive` (for example `'data=1G'` or
  `'osd-standalone=loop,2G,3'`).
- `add_machine` cannot be used with Kubernetes clouds.
- `pack_charm` skips `charmcraft pack` when the `<APP>_CHARM_PATH`
  environment variable is set; `deploy_local` reads the same environment
  variable when `located at '{path}'` is omitted.
- `scp_to_unit` copies into the remote user's home directory when
  `at '{remote_path}'` is omitted; `scp_from_unit` writes into the working
  directory using the basename of the remote path when
  `to '{local_path}'` is omitted.
- `wait_for` accepts fractional values (for example `'2.5'`).

## pytest-jubilant-bdd framework facts

- **Auto-registration.** The plugin registers via the `pytest11` entry
  point. Installing the package makes all built-in `@given`/`@when`/`@then`
  handlers available to pytest-bdd. Consumers **never import the step
  handlers** — only the public API below.
- **Public API** (`from pytest_jubilant_bdd import ...`): `Context`,
  `assertions`, `flexible`, `make_dict`, `make_list`,
  `make_storage_directive`. `Context` is the fixture type; the rest are
  helpers for authoring custom steps.
- **The `context` fixture** (session-scoped, provided by the plugin) yields
  a `Context` object. It replaces a hand-rolled `juju` fixture — do **not**
  define a `juju` fixture in the charm repo's `conftest.py`.
- **CLI options** registered by the plugin: `--juju-bdd-no-teardown` (skip
  model teardown) and `--juju-bdd-wait-timeout <sec>` (default 180s).
- **Failure diagnostics.** If any scenario fails, the plugin prints the
  last 1000 lines of each model's debug log to stdout at the end of the
  session.
- **Dependencies** (pulled in transitively): `jubilant ~= 1.0`,
  `pytest-bdd ~= 8.0`. Requires Python `>=3.12`.

## pytest-gherkinator execution ordering

`pytest-gherkinator` is a companion pytest plugin, install-activated via
the `pytest11` entry point (add it next to `pytest-jubilant-bdd`). Its
only contract with `gherkinator` is the classification tags rendered on
each generated `.feature` file; it never reads the YAML plans.
`pytest-bdd` turns Gherkin tags into pytest marks, and the plugin uses
those marks to order, skip, and filter scenarios:

- **Execution order.** Risk level first (`edge` → `beta` → `candidate` →
  `stable`), then test type within each risk level (`functional` →
  `solution` → `reliability` → `security` → `performance`). The sort is
  stable — scenarios sharing a classification keep their definition
  order, so within-feature dependency chains survive the cross-file sort.
- **Status skipping.** Scenarios whose plan status is `planned` or
  `deprecated` are skipped at runtime; only `implemented` scenarios
  execute.
- **Mark filtering.** All twelve classification values are registered
  marks:

  ```bash
  pytest -m edge                   # only edge-risk scenarios
  pytest -m implemented            # exclude planned/deprecated
  pytest -m "edge and functional"  # combine classifications
  ```

  This is how `edge.yaml` "gates every PR": CI runs `pytest -m edge`.

- **Running planned scenarios.** `planned` is a human-directed parking
  status. To execute a planned scenario while iterating, disable the
  plugin for that run: `pytest -p no:pytest-gherkinator <target>`.

Caveats:

- Ordering applies to single-process runs only; `pytest-xdist`
  distributes items to workers independently of execution order.
- Reordering plugins such as `pytest-randomly` can undo the ordering.
- Conflicting tags (for example feature `@edge` plus scenario `@beta`)
  make the scenario run unclassified with a warning; the plugin never
  guesses.
- Custom plan tags (for example `@multi-node`) become marks too, but are
  not registered by the plugin — register them in the charm repo's
  pytest configuration to silence `PytestUnknownMarkWarning`.

## Pattern mapping: existing jubilant test → YAML → BDD

The core translation table. The middle column shows where the pattern
lands in the YAML test plan; the right column shows the BDD equivalent
(exact phrasing in the built-in step table above).

| Existing jubilant pattern | Plan placement | BDD equivalent |
|---|---|---|
| `juju.add_model(...)` / `jubilant.temp_model()` | `background` or inline in `scenarios` | `Given I add model '{name}'` — the framework suffixes the real model name. Does **not** switch the active model: follow with `Given I switch to model '{model}'` if later steps omit `in model '{model}'` clauses. |
| `juju.deploy("charm", "app")` (Charmhub) | `scenarios[i]` steps | `Given I deploy '{app}' [from channel '{channel}'] [on base '{base}'] [with '{n}' units]` |
| `juju.deploy(local_charm, "app")` | `scenarios[i]` steps | `Given I deploy '{app}' from a local charm [located at '{path}']` — or set the `<APP>_CHARM_PATH` environment variable |
| `juju.integrate("a", "b")` | `scenarios[i]` steps | `Given I integrate '{a}' with '{b}'` |
| `juju.config("app", values={...})` | `scenarios[i]` steps | `Given I set '{key}' for app '{app}' to '{value}'` |
| `juju.config("app", reset=["key"])` | `scenarios[i]` steps | `Given I reset '{key}' for app '{app}'` |
| `juju.add_unit("app", num_units=n)` | `scenarios[i]` steps | `Given I add '{n}' units to app '{app}'` |
| `juju.remove_unit("app/N", force=True)` for a down/failed unit | custom step | The built-in `remove_unit` step has no `[forcibly]` clause — only `remove_app` does. Units whose machine is `down` require `force=True`: write a custom `@when` step that calls `juju.remove_unit(..., force=True)` directly. |
| `juju.run("app/0", "action", params=...)` | `scenarios[i]` steps | `When I run action '{action}' on unit '{u}' [with parameters '{k=v ...}']` — results pushed to `context.action_results`. Parameters are space-separated `k=v` pairs; lowercase `true`/`false` are cast to Python booleans. |
| `juju.exec("cmd", unit="app/0")` | `scenarios[i]` steps | `When I execute '{cmd}' on unit '{u}'` — results pushed to `context.exec_results`. |
| `juju.run(unit_A, "action")` where the action modifies state of a node on unit_B, then `juju.exec("... node <unit_B-name>", unit=unit_A)` | `scenarios[i]` steps | `When I run action '{action}' on unit '{unit_A}'` + custom `Then` referencing `unit '{unit_B}'` — the verification step must name the **node owner**, not the action executor. |
| `juju.wait(lambda s: s.apps["app"].status == "active")` | `scenarios[i]` steps | `Then the workload status for app '{app}' is 'active'` — the framework polls via `context.wait()`. `juju.wait()` is an assertion, not setup: do not hide it in a custom deploy `Given` step when integrations happen in later steps. |
| Custom status checker `def _ready(s): ...` passed to `juju.wait` | custom step | Keep as a helper, or wrap it in a custom `Then` step that calls `context.wait(ready=...)`. |
| `tenacity.Retrying(...)` around an assertion | `scenarios[i]` steps | Drop tenacity; use `context.wait()` (or a built-in `Then` step, which already polls). The `ready` function must catch `Exception` — not just `AssertionError` — because `juju.exec()`/`juju.run()` raise `jubilant.TaskError` on non-zero exit codes. |
| `sleep(N)` after `juju.wait()` | custom step with `context.wait()` | Charm `active` status does not guarantee installed binaries are on `PATH` yet. Poll for the binary (for example `juju.exec("apptainer --version")`) instead of a fixed sleep. |

## Wiring files

### `pyproject.toml`

Add `pytest-jubilant-bdd` and `pytest-gherkinator` to the project's dev
dependencies (the former pulls `jubilant` and `pytest-bdd` transitively;
the latter orders and filters scenario execution):

```toml
[project.optional-dependencies]
dev = [
    # ... existing dev dependencies ...
    "pytest-jubilant-bdd",
    "pytest-gherkinator",
]
```

### `tests/integration/constants.py`

Glob feature files by risk level so each test module loads the right set:

```python
"""Constants used within the charm's integration tests."""

from pathlib import Path

FEATURE_DIR = Path(__file__).parent.resolve() / "features"
EDGE_FEATURES = [str(feature) for feature in FEATURE_DIR.glob("*edge*")]
BETA_FEATURES = [str(feature) for feature in FEATURE_DIR.glob("*beta*")]

# App names used across scenarios and custom steps.
MY_APP_NAME = "my-app"
```

### `tests/integration/test_<risk>.py`

One test module per risk level. Loads scenarios by glob and defines custom
steps:

```python
"""BDD step definitions for <charm> <risk> tests."""

from pytest_bdd import parsers, scenarios, then
from pytest_jubilant_bdd import Context

from constants import EDGE_FEATURES

scenarios(*EDGE_FEATURES)


@then(parsers.parse("the output should be '{expected}'"))
def assert_output(context: Context, expected: str) -> None:
    """Assert the most recent exec result matches the expected output."""
    task = context.exec_results.peek()
    assert task.stdout.strip() == expected
```

### `conftest.py` — what NOT to write

Do **not** define a `juju` fixture, do **not** add `--base` /
`--keep-models` options, and do **not** import `jubilant`. The plugin
provides:

- The session-scoped `context` fixture (replaces `juju`).
- CLI options `--juju-bdd-no-teardown` and `--juju-bdd-wait-timeout <sec>`
  (default 180s).

A `conftest.py` is usually unnecessary. If one exists for other purposes
(e.g. `pytest_configure`), leave the Juju lifecycle to the plugin.

### `conftest.py` — what survives migration

A migrated repo already has a `conftest.py`. Keep charm-specific fixtures
and hooks; drop everything the plugin replaces:

```python
"""Integration test fixtures and shared step definitions."""
import pytest
from pytest_bdd import parsers, when

from pytest_jubilant_bdd import Context


@pytest.fixture(scope="session")
def charm_base(request: pytest.FixtureRequest) -> str:
    """Charm deployment base, overridable via --charm-base."""
    return request.config.getoption("--charm-base")


# Shared across multiple .feature files — must live in conftest.py
# because pytest-bdd resolves steps per-module.
@when(parsers.parse("I reset the node configuration on unit '{unit}'"))
def reset_node_config(context: Context, unit: str) -> None:
    """Reset node configuration via the set-node-config action."""
    juju = context.get_juju()
    juju.run(unit, "set-node-config", params={"reset": True})


def pytest_addoption(parser: pytest.PytestParser) -> None:
    """Add charm-specific CLI options."""
    parser.addoption("--charm-base", default="ubuntu@26.04")
```

- **Keep:** charm-specific fixtures (`charm_base` above), custom steps
  shared across feature files, pytest hooks (`pytest_addoption`,
  `pytest_configure`, opt-in gating — see § Opt-in test gating).
- **Drop:** the `juju` fixture (the plugin's `context` replaces it),
  custom options the plugin replaces (`--keep-models` →
  `--juju-bdd-no-teardown`), and any hand-rolled `jubilant` lifecycle
  management.
- Fixtures that need lifecycle management (starting/stopping an SMTP
  server, say) also belong here — plain step functions have no teardown
  hook.

## Feature file management (commit-and-diff)

Generated `.feature` files are committed alongside the YAML plans.
Drift between YAML and `.feature` files is caught by `gherkinator diff`
run from a `pre-commit` hook and/or CI. `just integration` runs `pytest`
directly — sync is enforced by the hooks, not the test run.

`tests/integration/mod.just`:

```just
# Compare generated feature files against test plans
diff *args:
    gherkinator diff {{ args }} plans/ features/

# Generate Gherkin feature files for integration tests
generate *args:
    gherkinator generate {{ args }} --output-dir=features/ plans/

# Validate integration test plans
validate:
    gherkinator validate plans/
```

By default `generate` and `diff` process every plan regardless of
classification. To render or check a specific slice, pass gherkinator's
filtering flags through the recipe:

```bash
just gherkinator generate --status=implemented  # only implemented plans
just gherkinator generate --status=planned      # only planned plans
just gherkinator diff --risk=edge               # edge-risk plans only
```

(`--risk` is cumulative — `--risk=beta` includes edge + beta.)

Root `justfile` wires the module:

```just
# Manage charm test plans with gherkinator
mod gherkinator "tests/integration/"
```

`just integration` runs pytest only — no gherkinator invocation:

```just
# Run integration tests
integration *args: lock
    #!/usr/bin/env bash
    set -euxo pipefail

    {{ uv_run }} pytest \
        -v \
        --tb native \
        -s \
        --log-cli-level=INFO \
        {{ args }} \
        {{ tests_dir / "integration" }}
```

`.pre-commit-config.yaml` (local hooks):

```yaml
repos:
  - repo: local
    hooks:
      - id: lint
        name: Lint
        entry: just lint
        language: system
        files: '\.py$'
        pass_filenames: false
      - id: typecheck
        name: Typecheck
        entry: just typecheck
        language: system
        files: '\.py$'
        pass_filenames: false
      - id: unit
        name: Unit tests
        entry: just unit
        language: system
        files: '\.py$'
        pass_filenames: false
      - id: gherkinator-validate
        name: Validate test plans
        entry: just gherkinator validate
        language: system
        files: '^tests/integration/plans/[^/]*\.ya?ml$'
        pass_filenames: false
      - id: gherkinator-diff
        name: Check test plans against generated feature files
        entry: just gherkinator diff
        language: system
        files: '^tests/integration/(features|plans)/[^/]*\.(ya?ml|feature)$'
        pass_filenames: false
```

Do **not** add `tests/integration/features/` to `.gitignore` — the feature
files must be committed so `gherkinator diff` can verify them against the
plans.

## gherkinator command quick reference

Install (snap recommended):

```bash
sudo snap install gherkinator --classic

# Or build from source:
git clone https://github.com/canonical/gherkinator.git
cd gherkinator && go build -o gherkinator .
```

| Command | Purpose |
|---------|---------|
| `gherkinator validate <inputs>` | Check plans against the schema |
| `gherkinator generate --format gh <inputs> -o <dir>` | Emit `.feature` files |
| `gherkinator generate --format md <inputs> -o <dir>` | Emit Markdown docs |
| `gherkinator serve <inputs>` | Live Sphinx docs site; rebuilds on YAML save |
| `gherkinator diff <plans> <features>` | CI drift check; exit 0 = in sync, 1 = diffs, 2 = error |
| `gherkinator delete -i <file> "<feature>"` | Remove a plan by feature name |
| `gherkinator clean -d <dir>` | Remove generated artifacts |

Notes:

- Input arguments accept any mix of `.yaml`/`.yml` files and directories
  (scanned non-recursively).
- `--risk` filtering is cumulative: `--risk beta` includes edge + beta.
- `--status` filters to a single status (`planned`, `implemented`,
  `deprecated`).
- Output filenames derive from the `feature` field.
- Full CLI usage (schema hints, `serve`, CI drift checking) is documented
  in the `gherkinator-cli` skill:
  https://github.com/canonical/gherkinator/tree/main/.agents/skills/gherkinator-cli.

## Context API essentials for custom steps

The authoritative reference is the `reusable-step-handler` skill in the
pytest-jubilant-bdd repo:
https://github.com/canonical/pytest-jubilant-bdd/blob/main/.agents/skills/reusable-step-handler/SKILL.md.
The essentials:

| API | Purpose |
|-----|---------|
| `context.get_juju(model=None)` | Per-model `jubilant.Juju` instance. Never construct `Juju()` directly. |
| `context.get_app(app, model=...)` | `AppStatus` from `juju status`. Raises `AppNotFoundError`, `TooManyDeployedAppsError`. |
| `context.get_apps(*apps, model=...)` | Batch `get_app` — requested apps (or every app) as a dict. |
| `context.get_unit(unit, model=...)` | `UnitStatus` from `juju status`. |
| `context.get_units(*units, model=...)` | Batch `get_unit` — requested units (or every unit) as a dict. |
| `context.action_results` | `stack[Task]` — results of `When I run action ...` |
| `context.exec_results` | `stack[Task]` — results of `When I execute ...` |
| `context.ssh_results` | `stack[str]` — stdout of `When I ssh into ... and I execute ...` |
| `context.scenario_state` | `dict[str, Any]` — share arbitrary values between steps of a scenario. |
| `context.wait(ready=lambda ctx: ..., timeout=...)` | Poll until `ready` returns `True` 3× consecutively. Raises `TimeoutError` on timeout. Pass `timeout=<seconds>` to override the global `--juju-bdd-wait-timeout` for a single wait. |
| `context.models` | `ModelMapping` of models added via `Given I add model ...` |
| `context.default_model` | Set via `Given I switch to model ...` |
| `assertions.app` / `.model` / `.unit` / `.storage` | Reusable assertion helpers — the same ones backing the built-in checkpoint handlers. |

Stack API: `push()`, `pop()`, `peek()`, `is_empty()`, `len()`.

## Migration fidelity checklist

The verification checklist at the end of this file confirms tooling and
schema. This checklist confirms **semantic equivalence** — that each
migrated scenario tests what its legacy test tested. Work through it after
the YAML and custom steps are written, before running the suite.

### Migration completeness

- [ ] Every legacy test has a YAML `TestPlan` equivalent (a scenario or a
      scenario outline).
- [ ] `<CHARM_NAME>_CHARM_PATH` environment variables are set where needed
      (for example `SLURMCTLD_CHARM_PATH`); `pack_charm` skips
      `charmcraft pack` and `deploy_local` reads the variable when
      `located at '{path}'` is omitted. The legacy `LOCAL_*` convention is
      superseded — migrate any `LOCAL_*` variables.
- [ ] Legacy `test_*.py` files are retained until the whole BDD suite is
      green.

### Assertions

- [ ] Every `assert` in the legacy test has a corresponding `Then` step.
      Common gap: a legacy test asserts multiple fields from one
      `juju.exec` result (for example `return_code`, `status`, `stdout`),
      but the BDD only checks one.
- [ ] Precondition assertions are preserved **and made explicit**. Legacy
      tests often assert starting state before an action (for example "3
      controllers, all UP" before scaling down). Migrate each to a `Given`
      so the scenario verifies its own starting state.
- [ ] Multi-app status checks are not narrowed. If the legacy waits on
      `all_active(*APPS)` (multiple apps), the BDD must check each app's
      status — not just the primary. Missing this means an error in a
      secondary app goes undetected until timeout.
- [ ] Identity/hostname preservation checks are migrated. If the legacy
      verifies that a specific unit remains primary after a topology
      change, the BDD must do the same — otherwise a failover to the wrong
      unit passes silently.

### Action parameters

- [ ] Every action parameter is preserved with the correct name, value,
      and type. Compare the `params={...}` dict in the legacy `juju.run`
      call against the `with parameters '{...}'` string and any custom step
      that re-parses it.
- [ ] Parameters with comma-containing values are not split incorrectly.
      If a legacy param value contains commas (for example
      `storage={"osd-standalone": "loop,2G,3"}`), a custom step that splits
      on `,` will corrupt it. Preserve the value as-is or use a different
      parsing strategy.

### Side effects and fixtures

- [ ] `fast_forward` / config restoration. If the legacy uses a
      function-scoped fixture that sets a config value and restores it
      after the test, the BDD must also restore it. A `Given` step that
      sets config without restoration leaks the value into subsequent
      scenarios.
- [ ] Role→unit mappings are snapshotted before topology-changing actions.
      If the legacy test captures which unit is primary/leader before a
      failover, the BDD must do the same: a `Given` records the mapping
      into `context.scenario_state`; subsequent steps read the snapshot
      rather than re-querying. See [examples.md](examples.md).
- [ ] `juju.wait_timeout` is preserved. If the legacy sets a long session
      timeout (for example `60*60`), verify that `context.wait()` calls use
      an equivalent timeout. The plugin default is 180s; override via
      `--juju-bdd-wait-timeout` or `Context(wait_timeout=...)`.
- [ ] Debug-log-on-failure is built in: if any scenario fails, the plugin
      prints the last 1000 lines of each model's debug log at the end of the
      session. A legacy `juju` fixture hook that printed
      `juju.debug_log()` on failure is superseded — do not re-implement it.
- [ ] Custom test options are replaced. Audit the legacy `conftest.py` for
      custom options (for example `--keep-models`, `--model`, `--bundle`)
      and map each to a plugin equivalent (`--keep-models` →
      `--juju-bdd-no-teardown`) or a new `conftest.py` hook.

### Polling and timing

- [ ] Fixed `sleep(N)` calls are replaced with `context.wait()` polling
      loops, not dropped entirely. A `sleep` after `juju.wait()` usually
      means the binary or service is not ready yet — poll for readiness
      instead.
- [ ] `tenacity.Retrying` retry semantics are preserved. The legacy retry
      count and wait interval may differ from `context.wait()` defaults (3
      consecutive successes, 1s delay, 180s timeout). If the legacy retried
      for longer, increase `context.wait(timeout=...)`.

### Markers

- [ ] Custom markers (for example `@pytest.mark.high_availability`) are
      applied via `pytestmark` on the scenario-loading module.
- [ ] `@pytest.mark.skip` is preserved via `pytestmark` on the
      scenario-loading module.

## Opt-in test gating

When a feature is slow or destructive (HA, failover, scale testing), gate
it behind an opt-in CLI flag. This requires three `conftest.py` hooks
working together:

```python
"""Opt-in gating for slow high-availability scenarios."""
import pytest


def pytest_addoption(parser: pytest.PytestParser) -> None:
    """Add the opt-in flag for high-availability tests."""
    parser.addoption(
        "--run-high-availability",
        action="store_true",
        default=False,
        help="run high availability tests (slow)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the high_availability marker."""
    config.addinivalue_line(
        "markers", "high_availability: marks tests as slow HA tests"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip high-availability tests unless the opt-in flag is set."""
    if config.getoption("--run-high-availability"):
        return
    skip_ha = pytest.mark.skip(reason="need --run-high-availability option to run")
    for item in items:
        if "high_availability" in item.keywords:
            item.add_marker(skip_ha)
```

Register the marker in `pytest_configure` (silences
`PytestUnknownMarkWarning`), register the flag in `pytest_addoption`, and
enforce the skip in `pytest_collection_modifyitems`. Combine with the
`pytestmark` list form on the scenario-loading module:

```python
"""BDD step definitions for high-availability tests."""
import pytest

pytestmark = [
    pytest.mark.high_availability,
]
```

```python
"""BDD step definitions for a known-broken deployment."""
import pytest

pytestmark = [
    pytest.mark.skip(reason="influxdb charm deployment is currently broken"),
]
```

## Troubleshooting

**`gherkinator validate` reports an invalid field**
- Check the message for the field name and the allowed enum values. Fix
  the YAML; do not hand-edit the generated `.feature` file.

**"Step not found" / "Ambiguous step"**
- Re-check the exact phrasing against the built-in step table above
  (single quotes, `I add model`, `I deploy ... from a local charm`, etc.).
- Ensure a custom step's `parsers.parse` pattern doesn't collide with a
  built-in step. Prefer the built-in.

**Eventually-consistent assertion fails intermittently**
- Use a built-in `Then` step (it already polls via `context.wait()`).
- For custom `Then` steps, call `context.wait(ready=...)` instead of
  `@retry`.

**`deploy_local` fails with `CharmNotFoundError`**
- Provide `located at '/path/to.charm'` in the step, or set the
  `<APP>_CHARM_PATH` environment variable (for example
  `SLURMCTLD_CHARM_PATH`).

**`TooManyDeployedAppsError`**
- More than one model has an app with the same name. Add
  `in model '{name}'` to the relevant step.

**`fixture 'X' not found`**
- The fixture is defined in a helper module (for example `bdd_utils.py`)
  instead of `conftest.py`. Move `@pytest.fixture` definitions to
  `conftest.py` — pytest does not discover fixtures from non-conftest,
  non-`test_*` modules.

**`StepDefinitionNotFoundError` for a custom step used in multiple
features**
- The step is defined in one `test_*.py` module but used by a `.feature`
  file loaded by a different module. pytest-bdd resolves steps per-module —
  move the step to `conftest.py`.

**`ValueError: option names {'--X'} already added`**
- pytest found two `conftest.py` files defining the same
  `pytest_addoption`. Check for accidentally duplicated directories
  (for example `tests/integration/integration/conftest.py`). Run
  `find . -name conftest.py -not -path "*/.venv/*"` to locate duplicates.

**`jubilant.TaskError` propagating from `context.wait()`**
- The `ready` function only catches `AssertionError`. Change it to
  `except Exception:` (see the non-negotiable rules in `SKILL.md` for
  why).

**`command not found` after charm reaches `active` status**
- Charm `active` status means reconciliation completed, but installed
  binaries may not be on `PATH` yet. Add a `context.wait()` polling loop
  that checks for the binary (for example
  `juju.exec("apptainer --version")`) before using it.

**Polling stuck / `context.wait()` times out after `set-node-state`**
- The `Then` step references the action's unit (for example
  `controller/0`) instead of the node owner (for example `compute/0`).
  Custom steps that derive node names from unit names will query the wrong
  node, and `context.wait()`'s `ready` catches `Exception`, so it retries
  silently until timeout. See the `set-node-state` example in
  [examples.md](examples.md).

**Step doesn't match when a field is empty (`""`)**
- `parsers.parse` defaults to `(.+)` which requires at least one
  character. Switch to `parsers.re` with `[^"]*` (or `[^']*`) so the field
  accepts empty strings:
  `r'and reason "(?P<reason>[^"]*)"'`.

## Verification checklist

Before declaring a migrated BDD suite complete:

- [ ] `just gherkinator validate` passes.
- [ ] `gherkinator generate` produces `.feature` files without errors.
- [ ] Generated `.feature` files are committed (not gitignored).
- [ ] `just gherkinator diff` exits 0 (plans and feature files in sync).
- [ ] `pytest tests/integration -v` passes (or `just integration`).
- [ ] No `juju` fixture defined in any `conftest.py`.
- [ ] No imports from `pytest_jubilant_bdd._main` in charm repo code.
- [ ] No hand-edited `.feature` files (regenerate instead).
- [ ] Every custom step has a PEP 257 docstring.
- [ ] Every drafted plan is `status: implemented`; `planned`/`deprecated`
      appear only where the user explicitly directed them.
- [ ] Scenarios execute in risk order (`edge` → `beta` → `candidate` →
      `stable`) — no reordering plugins (`pytest-randomly`,
      `pytest-xdist`) in play.
- [ ] Custom plan tags registered as marks in the charm repo's pytest
      config (no `PytestUnknownMarkWarning`).
- [ ] YAML plans and their generated `.feature` files are committed
      together in the same change.
- [ ] Every legacy test has a YAML `TestPlan` equivalent (see § Migration
      fidelity checklist).
- [ ] Legacy `test_*.py` files are retained until the whole BDD suite is
      green.
