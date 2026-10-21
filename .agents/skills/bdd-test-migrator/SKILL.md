---
name: bdd-test-migrator
description: 'Migrate an existing Juju charm repo''s jubilant-based pytest integration tests to BDD using gherkinator YAML test plans, pytest-jubilant-bdd, and pytest-gherkinator. Use when asked to "migrate tests to BDD", "convert to Gherkin", or "use pytest-jubilant-bdd" on a charm repo that already has jubilant integration tests. Do NOT use for greenfield BDD suites (use bdd-test-author) or the plugin''s own unit tests (use unit-testing).'
argument-hint: 'Path to the charm repository root, or leave blank to use the current directory.'
---

# Migrate existing jubilant integration tests to BDD

This skill converts a Juju charm repository's existing `jubilant`-based pytest
integration tests into behavior-driven tests: YAML test plans authored with
`gherkinator` (the single source of truth), `.feature` files generated from
them, reusable step handlers from `pytest-jubilant-bdd`, and risk/type-ordered
execution from `pytest-gherkinator`. The migration's core concern is
**translation fidelity** — each migrated scenario must test what its legacy
test tested.

Authoring a **greenfield** BDD suite (a charm with no existing integration
tests) is covered by the sibling `bdd-test-author` skill; this skill starts
from tests that already exist. Install `gherkinator` before authoring plans —
see the command quick reference in [reference.md](reference.md).

## When to use

- The user asks to "migrate", "convert", "Gherkin-ize", or "move to BDD" tests
  in a Juju charm repository.
- The target repo has `tests/integration/*.py` using `jubilant` directly (for
  example `jubilant.temp_model()`, `juju.deploy()`, `juju.wait()`) and no
  feature files.
- The repo contains charm markers (`charmcraft.yaml`, `metadata.yaml`,
  `src/charm.py`).

## When NOT to use

- Writing or testing reusable step handlers in the `pytest-jubilant-bdd` plugin
  itself — use `reusable-step-handler` and `unit-testing`.
- Authoring a greenfield BDD suite for a charm with no existing jubilant
  tests — use `bdd-test-author`.
- Running or troubleshooting the `gherkinator` CLI itself — use the
  `gherkinator-cli` skill at
  https://github.com/canonical/gherkinator/tree/main/.agents/skills/gherkinator-cli.
- The target repo does not already use `jubilant` — this is a migration skill,
  not a greenfield authoring guide.
- The user only wants to fix or extend existing BDD tests, not migrate
  non-BDD tests.
- Explaining framework internals (for example how `Context.wait()` polls)
  rather than migrating tests — see the `Context` API reference in
  [../reusable-step-handler/SKILL.md](../reusable-step-handler/SKILL.md).

## Non-negotiable rules

1. **`gherkinator` is always the entry point.** YAML test plans in
   `tests/integration/plans/` are the single source of truth. Never hand-edit
   generated `.feature` files — they are overwritten on every
   `gherkinator generate`.
2. **Never import step handlers from `pytest_jubilant_bdd._main`.** The plugin
   auto-registers all built-in `@given`/`@when`/`@then` handlers via the
   `pytest11` entry point. Consumers only import from the package root:
   `from pytest_jubilant_bdd import Context`.
3. **Never define a `juju` fixture in `conftest.py`.** The plugin provides the
   session-scoped `context` fixture, which replaces a hand-rolled
   `jubilant.Juju` fixture.
4. **Prefer built-in steps over custom steps.** Only write a custom step when
   no built-in step covers the behavior — check the phrasing table in
   [reference.md](reference.md) first.
5. **Do not modify production charm code to make a test pass.** Pause and ask
   the user.
6. **Every drafted plan is `status: implemented`.** Its scenarios run in the
   suite — and can fail it — as soon as it is committed. Only mark a plan
   `planned` or `deprecated` when the user explicitly directs it; status
   changes are a human-in-the-loop decision.
7. **Catch `Exception` (not just `AssertionError`) inside
   `context.wait(ready=...)` functions.** `juju.exec()` and `juju.run()`
   raise `jubilant.TaskError` on non-zero exit codes, and those errors are
   transient during node re-registration or service restarts.
   `context.wait()` only retries when `ready` returns `False` — an unhandled
   exception aborts the wait instead of retrying.
8. **Place fixtures and cross-feature custom steps in `conftest.py`.**
   pytest-bdd resolves step definitions per module — steps defined in one
   `test_*.py` are invisible to other test modules. pytest discovers
   fixtures only from `conftest.py` and `test_*` modules, never from helper
   modules like `bdd_utils.py`. Helper modules are for plain functions only.
9. **Distinguish the action-executing unit from the node-owning unit.** When
   a legacy test runs an action on one unit that modifies another unit's
   state, the `When` step references the action unit and the `Then`
   verification step must reference the node-owner unit — custom steps that
   derive names from the step text query the wrong node otherwise, and
   `context.wait()` retries silently until timeout. See
   [examples.md](examples.md).
10. **Snapshot role→unit mappings into `context.scenario_state` before
    failover actions.** A `Given` step records which unit holds each role
    (primary/backup, leader/follower); subsequent `When`/`Then` steps read
    the snapshot so they target the same physical unit even after the action
    shifts the role. See [examples.md](examples.md).
11. **Register state-checking handlers under both `@given` and `@then`** when
    the same check serves as precondition and attestation. Never stack
    `@when` with either.
12. **Qualify ambiguous nouns in custom step phrasing** (`controller`, `node`,
    `job`). Step definitions are global; terse nouns collide across features.
13. **Treat command-running preparation as `Given`, not `When`.** A step that
    runs a command only to prepare state (create pools, register a client,
    set up a mock device) is `Given`. Reserve `When` for the action under
    test.
14. **Do not invent `type`, `status`, or `risk` values** outside the enums
    enforced by `gherkinator validate`, and do not add reordering plugins
    (`pytest-randomly`, `pytest-xdist`) — they undo `pytest-gherkinator`'s
    ordering.
15. **Keep the legacy tests in place until the whole BDD suite is green.**
    Migrate in small plan-by-plan batches; delete legacy `test_*.py` files
    only when the migrated coverage is complete.

## Process

1. **Inspect the target repo.** Locate `tests/integration/**/*.py`,
   `conftest.py`, `charmcraft.yaml`, `metadata.yaml`. Identify which tests use
   `jubilant` directly and which fixtures and options the legacy
   `conftest.py` defines. Reference the pattern-mapping table in
   [reference.md](reference.md).

2. **Map each test to a scenario.** This is the core migration step. For
   every `def test_*(...)`:

   **Basic translation:**

   - Setup (deploys, models, config, integrations) → **Given** steps.
   - Actions (`juju.run`, `juju.exec`, config changes) → **When** steps.
   - Assertions (statuses, messages, command output, action results) →
     **Then** steps.
   - Group tests into logical features and assign each a risk level — one
     YAML file per risk level in `tests/integration/plans/`.

   **Judgment calls:**

   - **Shared setup across tests.** If multiple tests repeat the same deploy +
     integrate sequence, extract it into the feature's `background` block
     rather than duplicating it in every scenario. The background runs before
     every scenario in that feature.
   - **Chained legacy tests.** Lift each scenario's required starting state
     into `Given` preconditions; if a test genuinely cannot be decoupled from
     its siblings, propose a combined scenario.
   - **`juju.wait()` calls are assertions, not setup.** Map them to `Then the
     workload status for app '...' is 'active'`. Do not hide a `juju.wait()`
     inside a custom deploy `Given` step — a charm cannot reach `active`
     before its integrations exist.
   - **Polling / retry loops** (`tenacity.Retrying`, `@retry`, `sleep`).
     Drop them. Map the assertion inside the loop to a `Then` step — built-in
     `Then` steps already poll via `context.wait()`, and custom `Then` steps
     should call `context.wait(ready=...)` with `ready` catching `Exception`
     (rule 7).
   - **Side effects on a different unit.** The `When` uses the action unit;
     the `Then` uses the node-owner unit (rule 9 and the walkthrough in
     [examples.md](examples.md)).
   - **Multi-assertion tests.** A legacy test with several `assert` statements
     maps to several `Then` steps in one scenario — or to several scenarios if
     the assertions test different preconditions. Split by concern.
   - **Parametrized tests** (`@pytest.mark.parametrize`). Map to a `Scenario
     Outline` with an `Examples:` table, using `<param>` tokens in the
     scenario steps.
   - **Tests with no built-in equivalent.** Note these — each becomes a custom
     step defined in the risk level's `test_<risk>.py` module (or
     `conftest.py` if shared across features). Common candidates: running
     `scontrol` commands, checking Slurm node state, verifying munge key
     content, SMTP capture.
   - **Legacy cross-file order markers.** Not carried over — ordering comes
     from intra-feature definition order plus `pytest-gherkinator`'s risk/type
     ordering (§ Scenario design).

   Reference the pattern-mapping table and the migration fidelity checklist
   in [reference.md](reference.md).

3. **Scaffold the layout.** Create the directory structure and wiring files
   per [reference.md](reference.md): `plans/` (one YAML file per risk level),
   `features/` (generated, committed), `constants.py`, `test_<risk>.py`, and
   `mod.just`. Legacy `test_*.py` files are retained until the suite is
   green.

4. **Author the YAML test plans.** Write
   `tests/integration/plans/<risk>.yaml` directly, following the schema in
   [reference.md](reference.md). Author every plan with
   `status: implemented`. Validate in a loop until clean:

   ```bash
   just gherkinator validate
   # iterate on the YAML until: "All N test plan(s) are valid."
   ```

5. **Generate the `.feature` files.**

   ```bash
   just gherkinator generate
   ```

   Commit the generated `.feature` files together with the YAML plans;
   drift is caught by `just gherkinator diff` via pre-commit (§ Feature file
   management).

6. **Write custom step definitions** (only for domain logic with no built-in
   equivalent) in `tests/integration/test_<risk>.py`, or in `conftest.py` when
   shared across features. See § Custom steps and the templates in
   [examples.md](examples.md).

7. **Wire up the test modules.** `scenarios(*<RISK>_FEATURES)` from
   `constants.py`, and add `pytest-jubilant-bdd` and `pytest-gherkinator` to
   the integration test dependencies. See [reference.md](reference.md).

8. **Run the BDD suite** and confirm scenarios pass — via the repo's task
   runner:

   ```bash
   just integration          # just
   make integration          # make
   tox -e integration        # tox
   ```

   Charm repositories standardize on a task runner (`just`, `make`, or `tox`)
   as the single entrypoint — recipes embed preparatory steps like package
   installation, charm builds, and dependency resolution. Inspect the repo's
   task runner first to find the exact recipe name and any prerequisites it
   expects:

   - `just`: read the `justfile` (`just --list`, `just --show <recipe>`).
   - `make`: read the `Makefile` (`make help` if available).
   - `tox`: read `tox.ini` / `[tool.tox]` in `pyproject.toml` (`tox -av`).

   Run the recipe, not `pytest` directly. If the repo has no task runner,
   fall back to `pytest tests/integration -v` and note the gap.
   `pytest-gherkinator` orders scenarios by risk then type and skips
   `planned`/`deprecated` plans; scope runs with `-m` (for example
   `pytest -m edge`). Fix and rerun until green — newly migrated scenarios
   run in the suite and can fail it, so keep batches small and keep the
   legacy tests around until the whole suite is green.

## Scenario design

### Step ordering

- `Given` steps set up state (deploy, integrate, configure, add units).
- `When` steps perform the action under test (run actions, execute commands,
  ssh, scale, reconfigure).
- `Then` steps assert observable outcomes (statuses, messages, command
  output).

**Never interleave `When` and `Then` statements.** Consecutive `When` steps
run in order; all `Then` steps assert afterwards. If an assertion requires
running a command, fold the command execution into the `Then` step itself
(see the polled-`Then` templates in [examples.md](examples.md)) rather than
alternating `When I execute ...` / `Then ...` pairs.

### Scenario dependency ordering

Scenarios within a single feature file run in definition order. Use this to
build state incrementally:

- The **first scenario** deploys the stack.
- **Subsequent scenarios** begin with `Given '<app>' is deployed` (the
  `is_deployed` verification step) to assert — and rely on — the state
  established by earlier scenarios.

Across feature files, `pytest-gherkinator` orders execution by risk level
(`edge` → `beta` → `candidate` → `stable`), then by test type within each
risk level (`functional` → `solution` → `reliability` → `security` →
`performance`). The sort is stable, so scenarios sharing a classification
keep their definition order — the within-file dependency chains above
survive the cross-file sort.

Together these replace legacy cross-file order markers from traditional
jubilant test suites — leave the markers behind when migrating, and do not
add reordering plugins (`pytest-randomly`, `pytest-xdist`); they undo the
plugin's ordering.

### Risk levels

One YAML file per risk level in `tests/integration/plans/`:

| File | Contents |
|------|----------|
| `edge.yaml` | Fast, core-path tests that gate every PR. |
| `beta.yaml` | Broader coverage, less critical paths. |
| `candidate.yaml` | Pre-release validation. |
| `stable.yaml` | Full regression suite for stable releases. |

`type` reflects the nature of the test: `functional` for typical charm
behavior, `reliability` for HA/multi-unit/scale tests, `performance` for
benchmarks, `security` for access-control paths, `solution` for end-to-end
user workflows.

Every classification value is a registered pytest mark (via
`pytest-gherkinator`), so runs can be scoped with `-m`: `pytest -m edge`
gates a PR on edge-risk scenarios only, and `pytest -m "edge and
functional"` narrows further.

### Status lifecycle

- `implemented` — the default. Every drafted plan is authored as
  `status: implemented`, and its scenarios run in the suite.
- `planned` — parked, not expected to pass yet. Only mark a plan
  `planned` when the user explicitly directs it; `pytest-gherkinator`
  skips `planned` scenarios at runtime so they never fail the suite.
- `deprecated` — kept for history. Only mark a plan `deprecated` when the
  user explicitly directs it; its scenarios are skipped at runtime.

Status changes are a human-in-the-loop decision — never flip a plan's
status on your own initiative to make a suite pass.

### Multi-model tests

Use `Given I add model '<name>'` + `Given I switch to model '<name>'` for the
default, and scope individual steps with `in model '<name>'` clauses. See the
multi-model example in [examples.md](examples.md).

## Built-in step reference

The complete step phrasing table (Given / When / Then) is in
[reference.md](reference.md); the plugin's `README.md` lists every shipped
handler. Status values are fixed by the framework — never invent new ones in
YAML plans.

Key facts:

- Optional clauses are enclosed in `[...]` in the step phrasing and may
  appear in any order.
- Checkpoint handlers (`assert_all_agent_status`,
  `assert_workload_status`, `assert_workload_status_message`,
  `assert_storage_attached`, and `wait_for`) are registered as `Given`,
  `When`, and `Then` steps alike, so they can double as mid-scenario
  checkpoints via the `And`/`But` conjunctions. Polling checkpoints use
  `context.wait()` internally — no `tenacity` retry loops needed in custom
  steps — and accept an optional `within '{timeout}' seconds` clause that
  overrides the global `--juju-bdd-wait-timeout` for that step.
- `When I run action ...` pushes results onto `context.action_results`;
  `When I execute ...` pushes onto `context.exec_results`;
  `When I ssh into ... and I execute ...` pushes onto `context.ssh_results`.
  Action parameters are space-separated `k=v` pairs; lowercase `true`/`false`
  are cast to Python booleans.
- Several handlers are dual-registered as `Given` and `When` (`add_unit`,
  `integrate`, `disintegrate`, `remove_app`, `remove_unit`), so the same
  phrasing works in either stanza.
- Built-in coverage also includes machines (`add_machine`), storage
  (`add_storage`, `remove_storage`), cross-model offers (`create_offer`,
  `consume_offer`), file copy (`scp_to_unit`, `scp_from_unit`), and
  existence/config checks (`app_exists`, `unit_exists`,
  `is_app_config_set`). Check the phrasing table before writing a custom
  step.

## Custom steps

Write a custom step **only** when no built-in step covers the behavior.
Rules (aligned with `bdd-test-author`):

- Take `context: Context` as the first parameter.
- Use `context.get_juju(model)` for Juju access — never construct `Juju()`.
- Use `context.wait(ready=lambda ctx: ...)` for polling — never `tenacity`.
  The `ready` callable must catch `Exception`, not just `AssertionError`
  (rule 7).
- Use `parsers.parse("...")` for the step pattern.
- Add a PEP 257 docstring to every custom step function.
- Steps shared across multiple `.feature` files live in `conftest.py` —
  pytest-bdd resolves steps per-module (rule 8). Steps used by a single
  feature live in that risk level's `test_<risk>.py`.
- If a custom step proves reusable across charm repos, propose promoting it
  to a built-in handler in the `pytest-jubilant-bdd` plugin (see the
  `reusable-step-handler` skill) rather than duplicating it.

## Feature file management

Generated `.feature` files are **committed** alongside their YAML plans,
and drift between the two is caught by `gherkinator diff`:

- Feature files are generated artifacts — produce them with
  `gherkinator generate` (never hand-edit), then commit the result. Do not
  gitignore `tests/integration/features/`.
- A `mod.just` module in `tests/integration/` exposes the gherkinator
  subcommands: `just gherkinator generate`, `just gherkinator diff`, and
  `just gherkinator validate`. `generate` and `diff` render and check
  every plan by default; gherkinator's classification flags (`--status`,
  `--risk`) pass through to scope a run.
- A `pre-commit` hook (and/or CI step) runs `just gherkinator diff` to
  fail if committed `.feature` files diverge from the YAML source.
- `just integration` runs `pytest` directly; it does not invoke
  gherkinator. Sync is enforced by the hooks, not the test run.

Exact file contents (`mod.just`, root `justfile` wiring, and the
`pre-commit` config) are in [reference.md](reference.md).

## Stop and report if

- `gherkinator validate` reports a schema error — fix the YAML field, never
  the generated `.feature` output.
- A built-in step's phrasing doesn't match the Gherkin you wrote — re-read
  the step table in [reference.md](reference.md); built-in patterns are
  fixed.
- You're tempted to edit production charm code in the *target* charm repo to
  make a test pass — pause and ask the user.
- You're tempted to mark a test `planned` or `deprecated` to make a failing
  suite pass — pause and ask the user; status changes are human-directed.
- The target repo's `jubilant` API differs materially from the patterns in
  [reference.md](reference.md) — confirm the jubilant version and adjust
  custom-step guidance accordingly.
- A test needs a step the framework genuinely doesn't provide — propose a
  custom step to the user rather than forcing a built-in to fit.

## Supporting files

- [reference.md](reference.md) — complete directory layout, framework facts,
  execution ordering, the full built-in step phrasing table, wiring and
  `mod.just`/`pre-commit` templates, the jubilant → YAML → BDD
  pattern-mapping table, migration fidelity checklist, opt-in gating,
  troubleshooting, and the verification checklist.
- [examples.md](examples.md) — full before/after migrations: the YAML →
  validate → generate pipeline, custom-step templates, and the Slurm
  walkthroughs (GPU job polling, role→unit failover snapshots, binary
  availability after `active`, action-on-one-unit/state-on-another).

## Related resources

- Sibling skill `bdd-test-author` (greenfield BDD authoring):
  [../bdd-test-author/SKILL.md](../bdd-test-author/SKILL.md)
- Sibling skill `reusable-step-handler` — the authoritative `Context` API
  reference: [../reusable-step-handler/SKILL.md](../reusable-step-handler/SKILL.md)
- `gherkinator-cli` skill (CLI troubleshooting):
  https://github.com/canonical/gherkinator/tree/main/.agents/skills/gherkinator-cli
- gherkinator: https://github.com/canonical/gherkinator
- pytest-jubilant-bdd: https://github.com/canonical/pytest-jubilant-bdd
- jubilant: https://github.com/canonical/jubilant
- pytest-bdd: https://pytest-bdd.readthedocs.io/
- Gherkin reference: https://cucumber.io/docs/gherkin/reference/
