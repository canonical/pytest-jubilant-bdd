# bdd-test-migrator examples

Concrete before/after migrations translating **existing** jubilant tests
into gherkinator-controlled BDD. See `SKILL.md` for the workflow and
`reference.md` for the schema, phrasing table, and wiring. For greenfield
design guidance — designing scenarios from a charm's behavior rather than
migrating existing tests — see
[../bdd-test-author/examples.md](../bdd-test-author/examples.md).

## Full before/after pipeline

### Before (traditional pytest + jubilant)

```python
# tests/integration/test_charm.py
import pytest
import jubilant
import tenacity


def test_deploy_and_check(juju: jubilant.Juju) -> None:
    """Deploy slurmctld and check that get-password completes."""
    juju.deploy("slurmctld", "slurmctld", channel="latest/edge")
    juju.wait(lambda s: s.apps["slurmctld"].status == "active")

    result = juju.run("slurmctld/0", "get-password")

    for attempt in tenacity.Retrying(stop=tenacity.stop_after_attempt(5)):
        with attempt:
            assert result.return_code == 0
            assert result.status == "completed"
```

### After (gherkinator-controlled BDD)

**1. Author the YAML plan directly** in `tests/integration/plans/edge.yaml`
(one file per risk level). Write the YAML by hand and validate in a loop
until clean:

```bash
just gherkinator validate
# iterate on the YAML until: "All N test plan(s) are valid."
```

```yaml
feature: "Slurmctld deployment"
type: functional
status: implemented
risk: edge
description: "End-to-end deployment check for slurmctld."
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Deploy slurmctld and run get-password
    Given I deploy 'slurmctld' from channel 'latest/edge'
    When I run action 'get-password' on unit 'slurmctld/0'
    Then the workload status for app 'slurmctld' is 'active'
```

**2. Generate the `.feature` file:**

```bash
just gherkinator generate
# -> tests/integration/features/slurmctld_deployment.feature
```

Generated `slurmctld_deployment.feature`:

```gherkin
@functional @implemented @edge
Feature: Slurmctld deployment

  End-to-end deployment check for slurmctld.

  Background:
    Given I add model 'test'
    And I switch to model 'test'

  Scenario: Deploy slurmctld and run get-password
    Given I deploy 'slurmctld' from channel 'latest/edge'
    When I run action 'get-password' on unit 'slurmctld/0'
    Then the workload status for app 'slurmctld' is 'active'
```

**3. Load the scenarios** in `tests/integration/test_edge.py`:

```python
"""BDD step definitions for slurmctld edge tests."""

from pytest_bdd import scenarios

from constants import EDGE_FEATURES

scenarios(*EDGE_FEATURES)

# No custom steps needed — every step above is provided by
# pytest-jubilant-bdd. Action results are available on the `context`
# fixture (context.action_results) if a later scenario needs to inspect
# them.
```

**4. Run the suite** via the repo's task runner:

```bash
just integration          # just
make integration           # make
tox -e integration         # tox
# fall back to: pytest tests/integration -v
```

**5. Commit and sync.** Once green:

1. Verify sync: `just gherkinator diff` exits 0.
2. Commit the YAML plan and the generated `.feature` file together.

Status changes stay human-directed: every drafted plan is
`status: implemented` from the start, and `planned`/`deprecated` are applied
only when the user explicitly asks.

## Local-charm deploy example

The YAML input — `tests/integration/plans/beta.yaml`:

```yaml
feature: "Local charm deployment"
type: functional
status: implemented
risk: beta
description: "Deploy a locally built charm and configure it."
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Deploy a locally built charm with config
    Given I deploy 'slurmctld' from a local charm located at '/tmp/slurmctld.charm' with '3' units
    And I set 'debug' for app 'slurmctld' to 'true'
    Then the workload status for app 'slurmctld' is 'active'
```

Generated `.feature`:

```gherkin
@functional @implemented @beta
Feature: Local charm deployment

  Deploy a locally built charm and configure it.

  Background:
    Given I add model 'test'
    And I switch to model 'test'

  Scenario: Deploy a locally built charm with config
    Given I deploy 'slurmctld' from a local charm located at '/tmp/slurmctld.charm' with '3' units
    And I set 'debug' for app 'slurmctld' to 'true'
    Then the workload status for app 'slurmctld' is 'active'
```

Without `located at '...'`, the `deploy_local` step reads the
`SLURMCTLD_CHARM_PATH` environment variable (see `reference.md`).

## Multi-model integration example

The YAML input:

```yaml
feature: "Cross-model integration"
type: reliability
status: implemented
risk: candidate
description: "Integrate slurmctld and slurmd across two models."
scenarios:
  - |-
    Integrate slurmctld and slurmd across models
    Given I add model 'controller'
    And I switch to model 'controller'
    And I add model 'compute'
    And I deploy 'slurmctld' in model 'controller'
    And I deploy 'slurmd' in model 'compute'
    And I integrate 'slurmctld' with 'slurmd'
    Then all agents are 'idle' in models 'controller' and 'compute'
```

Note this plan uses `type: reliability` (multi-unit / multi-model
integration test) instead of `functional`. Pick the type that matches the
nature of the test. `Given I add model '...'` does **not** switch the active
model — the `Given I switch to model 'controller'` step makes `controller`
the default for steps that omit `in model '{model}'` clauses.

## Parametrised scenario (Scenario Outline) example

The YAML input — when `examples` is present and the scenario steps
reference `<param>` tokens, gherkinator emits a `Scenario Outline:`:

```yaml
feature: "Multi-user access"
type: functional
status: implemented
risk: beta
description: "Same access flow exercised for several users."
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Grant access by role
    Given I deploy 'access-manager' from channel 'latest/edge'
    When I run action 'grant' on unit 'access-manager/0' with parameters 'username=<username> role=<role>'
    Then the workload status for app 'access-manager' is 'active'
examples:
  - - alice
    - admin
  - - bob
    - viewer
```

Generated `.feature`:

```gherkin
@functional @implemented @beta
Feature: Multi-user access

  Same access flow exercised for several users.

  Background:
    Given I add model 'test'
    And I switch to model 'test'

  Scenario Outline: Grant access by role
    Given I deploy 'access-manager' from channel 'latest/edge'
    When I run action 'grant' on unit 'access-manager/0' with parameters 'username=<username> role=<role>'
    Then the workload status for app 'access-manager' is 'active'

    Examples:
      | username | role |
      | alice | admin |
      | bob | viewer |
```

## Multi-document YAML (one file, many features)

A single plan file can hold many features separated by `---`; each
document becomes one `.feature` file on generation. The convention is one
file per risk level, so documents sharing a file share its risk — here,
three plans in `tests/integration/plans/beta.yaml`:

```yaml
feature: "Slurmctld deployment"
type: functional
status: implemented
risk: beta
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Deploy slurmctld
    Given I deploy 'slurmctld' from channel 'latest/edge'
    Then the workload status for app 'slurmctld' is 'active'
---
feature: "Slurmd deployment"
type: functional
status: implemented
risk: beta
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Deploy slurmd
    Given I deploy 'slurmd' from channel 'latest/edge'
    Then the workload status for app 'slurmd' is 'active'
---
feature: "Cross-model integration"
type: reliability
status: implemented
risk: beta
scenarios:
  - |-
    Integrate slurmctld and slurmd
    Given I add model 'controller'
    And I switch to model 'controller'
    And I add model 'compute'
    And I deploy 'slurmctld' in model 'controller'
    And I deploy 'slurmd' in model 'compute'
    And I integrate 'slurmctld' with 'slurmd'
    Then all agents are 'idle' in models 'controller' and 'compute'
```

Running:

```bash
just gherkinator validate
just gherkinator generate
```

produces three `.feature` files in one shot:
`slurmctld_deployment.feature`, `slurmd_deployment.feature`,
`cross_model_integration.feature`. Each `test_<risk>.py` module loads its
own set via the `constants.py` globs.

## Incremental migration

A full-suite migration spans days. Work in small plan-by-plan batches:

1. Migrate a handful of related tests into one plan document.
2. Validate, generate, wire, and run until that batch is green.
3. Commit the plan and its `.feature` file together.
4. Repeat.

Legacy `test_*.py` files stay in place until the whole BDD suite is green —
newly migrated scenarios run (and can fail) in the suite as soon as they
are committed, so small batches keep failures scoped while the migration
is in progress.

To generate only a subset while iterating, pass gherkinator's filtering
flags through the recipe:

```bash
just gherkinator generate --risk=edge   # --risk is cumulative: edge only
just gherkinator generate --risk=beta   # edge + beta
```

`--status` filtering remains a gherkinator CLI capability (see the command
quick reference in `reference.md`); it is relevant when the human directs
`planned` parking, but newly migrated plans are authored
`status: implemented` and are not filtered by status during migration.

## Removing a plan you no longer want

If a plan turns out to be the wrong granularity, drop it via
`gherkinator delete`:

```bash
# Interactive confirmation
gherkinator delete -i tests/integration/plans/beta.yaml \
  "Slurmctld deployment"

# Non-interactive
gherkinator delete -y -i tests/integration/plans/beta.yaml \
  "Slurmctld deployment"
```

Then regenerate to drop the matching `.feature` file:

```bash
just gherkinator generate
```

If the directory is cluttered with stale `.feature` files from old plans,
nuke and regenerate:

```bash
gherkinator clean -d tests/integration/features
just gherkinator generate
```

## Custom step templates

> This section covers **charm-repo ad-hoc custom steps** — step
> definitions written in your own `conftest.py` or `test_<risk>.py` to
> extend the built-in handlers. If you are adding a new built-in step
> handler to the `pytest-jubilant-bdd` plugin itself, see the
> **`reusable-step-handler`** skill
> ([../reusable-step-handler/SKILL.md](../reusable-step-handler/SKILL.md))
> instead — it covers parser selection (`parse` vs `flexible` vs `re`),
> `%…%` block syntax, private-helper patterns, error class conventions,
> and unit-test wiring.

Custom steps take the `context` fixture and use `context.wait()` for
polling. For the exact `Context` API, defer to the
`reusable-step-handler` skill; the `Exception`-catching and
`conftest.py` placement rules are in `SKILL.md`.

### Inspecting action / exec results

```python
"""Custom steps for action-result assertions."""
from pytest_bdd import parsers, then

from pytest_jubilant_bdd import Context


@then(parsers.parse("the action should succeed"))
def assert_action_succeeded(context: Context) -> None:
    """Assert the most recent action completed with return code 0."""
    task = context.action_results.peek()
    assert task.status == "completed"
    assert task.return_code == 0
```

### Custom status / command check with polling

`context.wait()` polls `ready` until it returns `True` three times in a
row, then returns; it raises `TimeoutError` on timeout. See `SKILL.md`
for why `ready` must catch `Exception`.

```python
"""Custom steps for polled status-message assertions."""
from pytest_bdd import parsers, then

from pytest_jubilant_bdd import Context


@then(
    parsers.parse(
        "the unit '{unit}' workload message contains '{substring}'"
    )
)
def assert_message_contains(
    context: Context, unit: str, substring: str
) -> None:
    """Wait until the unit's workload status message contains substring."""
    context.wait(
        ready=lambda ctx: substring in ctx.get_unit(unit).workload_status.message,
    )
```

### GPU job submission polling

From `canonical/slurm-charms` — a `juju.exec`-based poll where the command
may fail transiently, so the call is wrapped in a try/except inside
`ready`:

```python
"""Custom steps for GPU job scheduling checks."""
from pytest_bdd import parsers, then

from pytest_jubilant_bdd import Context


@then(
    parsers.parse(
        "a slurm gpu job submitted from unit '{login_unit}' "
        "runs on unit '{compute_unit}'"
    )
)
def gpu_job_submission(
    context: Context, login_unit: str, compute_unit: str
) -> None:
    """Submit a GPU-requesting job and verify it runs on the compute node."""
    juju = context.get_juju()
    slurmd_result = juju.exec("hostname -s", unit=compute_unit)

    def ready(_ctx: Context) -> bool:
        try:
            sackd_result = juju.exec(
                "srun --partition compute --gres gpu:1 hostname -s",
                unit=login_unit,
            )
            assert sackd_result.stdout == slurmd_result.stdout
            return True
        except Exception:
            # juju.exec raises jubilant.TaskError transiently while Slurm
            # re-registers nodes — retry until the job lands.
            return False

    context.wait(ready=ready)
```

### Shared state within a scenario

Use `context.scenario_state` (a `dict[str, Any]` on the context, scoped to
the scenario) when a legacy test captures state before an action and
asserts it changed after — e.g., capture an initial key in a `Given` step,
run a rotation action in a `When` step, then assert the key changed in a
`Then` step. No fixture definition is needed. Use `And` to chain multiple
`Given` captures in the YAML before the `When` step.

```python
"""Custom steps that share state within one scenario."""
from pytest_bdd import parsers, then, when

from pytest_jubilant_bdd import Context


@when(parsers.parse("I capture the output of '{command}' on unit '{unit}'"))
def capture_output(context: Context, command: str, unit: str) -> None:
    """Capture command stdout into per-scenario shared state."""
    result = context.get_juju().exec(command, unit=unit)
    context.scenario_state["stdout"] = result.stdout


@then(parsers.parse("the captured output should be '{expected}'"))
def assert_captured(context: Context, expected: str) -> None:
    """Assert the captured stdout matches the expected value."""
    assert context.scenario_state["stdout"] == expected
```

### Snapshotting a role→unit mapping before a failover

Use `context.scenario_state` to snapshot a **role→unit mapping**
(primary/replica, leader/follower) *before* an action that shifts which
unit holds the role. Without the snapshot, a `When` step that re-queries
mid-failover may target the *new* primary and act on the wrong unit.

The example below is generic (no Slurm specifics) and also demonstrates
dual `@given`/`@then` registration.

> **Rule of thumb.** Stack `@given` and `@then` on handlers that only
> *check* state. Never stack `@when` — it's for actions under test.

#### `conftest.py`

```python
"""Shared steps for acme primary/replica failover scenarios."""
import json

from pytest_bdd import given, parsers, then, when

from pytest_jubilant_bdd import Context


def _query_roles(context: Context) -> dict:
    """Query live role-to-unit assignments from the service."""
    juju = context.get_juju()
    out = juju.exec("acmectl ping -j", unit="acme/0").stdout
    return json.loads(out)


def _roles(context: Context) -> dict:
    """Return the recorded snapshot if present, else query fresh."""
    if "roles" in context.scenario_state:
        return context.scenario_state["roles"]
    return _query_roles(context)


@given("I record the current role assignments")
def record_roles(context: Context) -> None:
    """Snapshot the current role-to-unit mapping for stable references."""
    context.scenario_state["roles"] = _query_roles(context)


# Stacked @given + @then: same handler, two keywords.
@given(parsers.parse("the acme service that is {role} reports status '{status}'"))
@then(parsers.parse("the acme service that is {role} reports status '{status}'"))
def role_status(context: Context, role: str, status: str) -> None:
    """Assert the service in the given role reports the given status."""

    def ready(_ctx: Context) -> bool:
        try:
            current = _query_roles(context)
            assert role in current, f"role '{role}' not found"
            assert current[role]["status"] == status
            return True
        except Exception:
            return False

    context.wait(ready=ready)


@when("I stop the acme service on the unit that is primary")
def stop_primary(context: Context) -> None:
    """Stop the acme service on the recorded primary unit."""
    juju = context.get_juju()
    roles = _roles(context)  # snapshot, not fresh query
    juju.exec("sudo systemctl stop acme", unit=roles["primary"]["unit"])
```

#### YAML test plan

```yaml
feature: "Acme high availability"
type: reliability
status: implemented
risk: stable
description: "Failover and recovery for the acme primary/replica service."
background: |-
  Given I add model 'test'
  And I switch to model 'test'
scenarios:
  - |-
    Service failover to replica
    Given I record the current role assignments
    And the acme service that is primary reports status 'UP'
    And the acme service that is replica reports status 'UP'
    When I stop the acme service on the unit that is primary
    Then the acme service that is replica reports status 'UP'
    And the acme service on the unit that is replica is running as primary
  - |-
    Service recovery after restarting primary
    Given I record the current role assignments
    And the acme service that is primary reports status 'DOWN'
    And the acme service that is replica reports status 'UP'
    When I restart the acme service on the unit that is primary
    Then the acme service that is primary reports status 'UP'
    And the acme service on the unit that is primary is running as primary
    And the acme service on the unit that is replica is running in background mode
```

### Custom step shared across feature files

If a custom step is used by scenarios in multiple `.feature` files, define
it in `conftest.py`:

```python
# conftest.py
"""Shared custom steps for all integration test modules."""
from pytest_bdd import parsers, when

from pytest_jubilant_bdd import Context


@when(parsers.parse("I reset the node configuration on unit '{unit}'"))
def reset_node_config(context: Context, unit: str) -> None:
    """Custom step available to ALL test_* modules."""
    juju = context.get_juju()
    juju.run(unit, "set-node-config", params={"reset": True})
```

### Binary availability after `active` status

A charm reaching `active` status means its reconciliation loop has
completed, but binaries it installs may not be immediately available on
the unit's `PATH`. When migrating tests that had `sleep(N)` after
`juju.wait()`, replace the fixed sleep with a `context.wait()` polling
loop that checks for the binary.

#### Before (traditional pytest + jubilant — from `canonical/slurm-charms` `test_oci_runtime.py`)

```python
def setup_apptainer(juju: jubilant.Juju) -> None:
    """Deploy and integrate `apptainer` with `slurmctld` and `slurmd`.

    Notes:
        - Sleep for five seconds after the `apptainer` app reaches active
          status to give the cluster enough time to reconfigure.
    """
    juju.deploy(APPTAINER_APP_NAME, channel="latest/edge")
    juju.integrate(APPTAINER_APP_NAME, SLURMCTLD_APP_NAME)
    juju.integrate(APPTAINER_APP_NAME, SLURMD_APP_NAME)
    juju.wait(lambda status: jubilant.all_active(status, APPTAINER_APP_NAME))
    sleep(5)  # <-- apptainer binary may not be on PATH yet


def test_apptainer_oci_scheduling(juju: jubilant.Juju) -> None:
    """Test that Slurm can schedule jobs using Apptainer."""
    if APPTAINER_APP_NAME not in juju.status().apps:
        setup_apptainer(juju)

    sackd_unit = f"{SACKD_APP_NAME}/0"
    slurmd_unit = f"{SLURMD_APP_NAME}/0"

    juju.exec(
        "apptainer pull /tmp/jammy.sif docker://ghcr.io/charmed-hpc/ubuntu-test:jammy",
        unit=slurmd_unit,
    )
    result = juju.exec(
        f"cd /tmp; srun -p {SLURMD_APP_NAME} --container=/tmp/jammy.sif cat /etc/os-release",
        unit=sackd_unit,
    ).stdout.strip()
    # ... assertions on result
```

#### After (gherkinator-controlled BDD)

The deploy, integrate, and status-wait all map to built-in steps — no
custom deploy handler. The `sleep(5)` becomes a `context.wait()` poll
inside the custom `Then` step:

```yaml
scenarios:
  - |-
    Apptainer OCI scheduling
    Given I deploy 'apptainer' from channel 'latest/edge'
    And I integrate 'apptainer' with 'slurmctld'
    And I integrate 'apptainer' with 'slurmd'
    Then the workload status for app 'apptainer' is 'active'
    And an apptainer container job submitted from unit 'sackd/0' runs on unit 'slurmd/0'
```

```python
"""Custom steps for apptainer OCI scheduling checks."""
from pytest_bdd import parsers, then

from pytest_jubilant_bdd import Context


@then(
    parsers.parse(
        "an apptainer container job submitted from unit '{login_unit}' "
        "runs on unit '{compute_unit}'"
    )
)
def apptainer_oci_scheduling(
    context: Context, login_unit: str, compute_unit: str
) -> None:
    """Pull an OCI image and run a Slurm job inside an Apptainer container."""
    juju = context.get_juju()

    # Replace sleep(5) — poll until the apptainer binary is on PATH.
    def apptainer_ready(_ctx: Context) -> bool:
        try:
            juju.exec("apptainer --version", unit=compute_unit)
            return True
        except Exception:
            return False

    context.wait(ready=apptainer_ready)

    juju.exec(
        "apptainer pull /tmp/jammy.sif docker://ghcr.io/charmed-hpc/ubuntu-test:jammy",
        unit=compute_unit,
    )
    # ... rest of the test
```

## Migrating action-on-one-unit / state-on-another tests

Some charm actions run on one unit but modify state belonging to a
different unit. In Slurm, `set-node-state` runs on `slurmctld/0` but
changes the state of a node registered to `slurmd/0` / `compute/0`.
The legacy test uses two distinct variables; the YAML test plan has a
single `unit` field per step, so each step must reference the correct
unit.

### Before (traditional pytest + jubilant)

```python
slurmctld_unit = f"{SLURMCTLD_APP_NAME}/0"   # action executor
slurmd_unit = f"{SLURMD_APP_NAME}/0"          # node owner
name = slurmd_unit.replace("/", "-")           # -> "compute-0"

juju.run(slurmctld_unit, "set-node-state",
         params={"nodes": name, "state": "down", "reason": "maintenance"})
result = juju.exec(f"scontrol --json show node {name}", unit=slurmctld_unit)
```

### After — correct YAML (action unit ≠ verification unit)

```yaml
scenarios:
  - |-
    Set node state action updates node state and reason
    When I run action 'set-node-state' on unit 'controller/0' with parameters 'nodes=compute-0 state=down reason=maintenance'
    Then the node for unit 'compute/0' has state containing 'DOWN' and reason "'maintenance'"
```

`When` uses `controller/0` (action executor); `Then` uses `compute/0`
(node owner) so `node_name("compute/0")` → `compute-0` matches the
node the action modified.

### Common pitfall — same unit in both steps

```yaml
# WRONG — will silently time out
When I run action 'set-node-state' on unit 'controller/0' with parameters 'nodes=compute-0 state=down reason=maintenance'
Then the node for unit 'controller/0' has state containing 'DOWN' and reason "'maintenance'"
```

`node_name("controller/0")` → `controller-0`, which is not a registered
compute node. `context.wait()` catches the exception and retries silently
until the 3-minute timeout, making it appear "stuck" rather than failing
with a clear assertion error.
