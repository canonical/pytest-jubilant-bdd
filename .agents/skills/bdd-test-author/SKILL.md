---
name: bdd-test-author
description: 'Author novel (greenfield) BDD integration tests for a Juju charm repo using gherkinator YAML test plans, pytest-jubilant-bdd, and pytest-gherkinator. Use when writing new Gherkin-based integration tests from scratch for a charm that does not yet have BDD tests, when scaffolding the tests/integration directory layout, or when deciding how to structure scenarios, custom steps, and risk-level test plans. Do NOT use for writing the plugin''s own unit tests (use unit-testing).'
argument-hint: 'Path to the charm repository root, or leave blank to use the current directory.'
---

# Author greenfield BDD integration tests

This skill covers writing **new** behavior-driven integration tests for a Juju
charm repository using `gherkinator` (YAML test plans as the single source of
truth), `pytest-jubilant-bdd` (reusable Gherkin step handlers), and
`pytest-gherkinator` (risk/type-ordered, status-filtered scenario
execution). It walks the full authoring lifecycle: designing scenarios from
the charm's documented behavior, scaffolding the `tests/integration/`
layout, authoring and validating YAML test plans, generating `.feature`
files, and writing custom steps where the built-in handlers fall short.

## When to use

- A charm repo has no integration tests (or only non-BDD tests) and needs new
  BDD tests designed from the charm's documented behavior.
- A new charm is being scaffolded and needs the full `tests/integration/`
  BDD layout created.
- New scenarios need to be added to an existing BDD test plan.
- A contributor asks "how should I structure tests for this charm?".

## When NOT to use

- Writing or testing reusable step handlers in the `pytest-jubilant-bdd`
  plugin itself — use `reusable-step-handler` and `unit-testing`.
- Running or troubleshooting the `gherkinator` CLI itself — use the
  `gherkinator-cli` skill at
  https://github.com/canonical/gherkinator/tree/main/.agents/skills/gherkinator-cli.
- Migrating an existing (non-BDD) jubilant test suite to BDD — use
  `bdd-test-migrator`.

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
   no built-in step covers the behavior. See § Custom steps.
5. **Do not modify production charm code to make a test pass.** Pause and ask
   the user.
6. **Every drafted plan is `status: implemented`.** Only mark a plan
   `planned` or `deprecated` when the user explicitly directs it — status
   changes are a human-in-the-loop decision.

## Process

1. **Understand the charm.** Read `charmcraft.yaml`, `metadata.yaml`,
   `src/charm.py`, and any existing docs. Identify:
   - What applications this charm needs deployed alongside it (principals,
     integrations, external services like databases).
   - What actions it exposes and what config options matter.
   - What observable outcomes exist (workload statuses, status messages,
     files on disk, service states, command output).
2. **Design scenarios.** Map each behavior to a scenario. Setup → `Given`,
   actions → `When`, assertions → `Then`. Group scenarios into one feature
   per risk level. See § Scenario design.
3. **Scaffold the layout.** Create the directory structure and wiring files
   per [reference.md](reference.md).
4. **Author the YAML test plan.** Write
   `tests/integration/plans/<risk>.yaml` following the schema in
   [reference.md](reference.md). Author every plan with
   `status: implemented`; only mark a plan `planned` or `deprecated`
   when the user explicitly directs it.
5. **Validate and generate.**

   ```bash
   just gherkinator validate
   just gherkinator generate
   ```

   Commit the generated `.feature` files together with the YAML plans.
   `just gherkinator generate` renders every plan by default; pass a
   classification filter through when a subset is needed (for example
   `just gherkinator generate --status=implemented`).

6. **Write custom steps** (only where built-ins fall short) in
   `tests/integration/test_<risk>.py`. See § Custom steps.
7. **Wire up the test module.** `scenarios(*<RISK>_FEATURES)` from
   `constants.py`. See [reference.md](reference.md).
8. **Run the suite.** `just integration` (or
   `pytest tests/integration -v`). `pytest-gherkinator` orders scenarios
   by risk level then test type and skips any `planned`/`deprecated`
   plans; scope runs with `-m` (for example `pytest -m edge`). Fix and
   rerun until green.

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
(see the `assert_node_registered` pattern in
[examples.md](examples.md)) rather than alternating
`When I execute ...` / `Then ...` pairs.

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

Together these replace `@pytest.mark.order` and `pytest-order` from
traditional jubilant test suites. Do not add reordering plugins
(`pytest-randomly`, `pytest-xdist`) — they undo the plugin's ordering.

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
- `deprecated` — kept for history. Only mark a plan `deprecated` when
  the user explicitly directs it; its scenarios are skipped at runtime.

Status changes are a human-in-the-loop decision — never flip a plan's
status on your own initiative to make a suite pass.

### Multi-model tests

Use `Given I add model '<name>'` + `Given I switch to model '<name>'` for the
default, and scope individual steps with `in model '<name>'` clauses. See the
two-model example in [examples.md](examples.md).

## Built-in step reference

The complete step phrasing table (Given / When / Then) is in
[reference.md](reference.md); the plugin's `README.md` lists every shipped
handler. Status values are fixed by the framework — never invent new ones
in YAML plans.

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
Common categories observed in real charm repos:

| Category | Example phrasing | Implementation |
|----------|------------------|----------------|
| Output assertion | `Then the output should be '{expected}'` | `context.exec_results.peek().stdout` |
| SSH output field | `Then the ssh output field '{field}' should be '{value}'` | `context.ssh_results.pop()` |
| Domain setup | `Given I configure 'ldap-integrator' with data from 'openldap'` | Direct `context.get_juju()` calls |
| Command + assert (polled) | `Then the node '{name}' should be registered with Slurm on unit '{unit}'` | `context.wait()` around a `juju.exec` call |

Custom step rules:

- Take `context: Context` as the first parameter.
- Use `context.get_juju(model)` for Juju access — never construct `Juju()`.
- Use `context.wait(ready=lambda ctx: ...)` for polling — never `tenacity`.
- Use `parsers.parse("...")` for the step pattern.
- Add a PEP 257 docstring to every custom step function.
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
- You're tempted to edit production charm code to make a test pass — pause
  and ask the user.
- You're tempted to mark a test `planned` or `deprecated` to make a failing
  suite pass — pause and ask the user; status changes are human-directed.
- The behavior under test genuinely has no built-in step and no reasonable
  custom step — propose the design to the user before forcing it.

## Supporting files

- [reference.md](reference.md) — complete directory layout, framework
  facts, execution ordering, `pyproject.toml` and `justfile` snippets,
  `constants.py` / `mod.just` / `pre-commit` templates, the full built-in
  step phrasing table, and the YAML schema.
- [examples.md](examples.md) — full greenfield walkthroughs: designing
  scenarios from a charm's behavior, the YAML plan, generated feature file,
  custom steps, and multi-model / polled-assertion / file-copy / offer /
  storage / machine patterns.
