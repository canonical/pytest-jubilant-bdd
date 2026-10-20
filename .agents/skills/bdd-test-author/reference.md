# bdd-test-author reference

Complete reference for authoring greenfield BDD integration tests with
`gherkinator` and `pytest-jubilant-bdd`.

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
└── mod.just                 # gherkinator subcommands (generate / diff / validate)
```

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
| `gherkinator init <dir> --name <file>` | Scaffold a test plan directory |
| `gherkinator edit <file>` | Open in `$EDITOR` with schema help; validates on save |
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

## Verification checklist

Before declaring a greenfield BDD suite complete:

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
