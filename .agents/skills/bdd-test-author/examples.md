# bdd-test-author examples

Full greenfield walkthroughs showing how to design BDD tests for a charm
from scratch. Patterns are drawn from `canonical/sssd-operator`,
`canonical/apptainer-operator`, and the `pytest-jubilant-bdd` and
`pytest-gherkinator` plugins.

## Example 1: Scaffolding a new charm's edge tests

Suppose a new charm `foo-operator` exposes:

- A `juju-info` integration requiring a principal charm.
- A `get-config` action returning JSON.
- Active status when configured, blocked when misconfigured.

### Step 1 — Design scenarios

| Behavior | Scenario | Steps |
|----------|----------|-------|
| Deploys with a principal | `Deploy the foo charm with a principal charm` | pack, add model, deploy, integrate, assert idle + active |
| Action returns config | `Run the get-config action` | `Given 'foo' is deployed`, run action, assert result |
| Blocks when misconfigured | `Misconfigure the foo charm` | `Given 'foo' is deployed`, set bad config, assert blocked + message |

### Step 2 — Scaffold the layout

```bash
mkdir -p tests/integration/{plans,features,assets}
```

Create `tests/integration/constants.py`:

```python
"""Constants used within the foo charm's integration tests."""

from pathlib import Path

FEATURE_DIR = Path(__file__).parent.resolve() / "features"
EDGE_FEATURES = [str(feature) for feature in FEATURE_DIR.glob("*edge*")]

FOO_APP_NAME = "foo"
UBUNTU_APP_NAME = "ubuntu"
```

### Step 3 — Author the YAML plan

`tests/integration/plans/edge.yaml`:

```yaml
---
feature: "Functional edge tests"
type: functional
status: implemented
risk: edge
description: >
  Functional tests for the edge risk level
scenarios:
  - |-
    Deploy the foo charm with a principal charm

    Given I pack a 'foo' charm
    And I add model 'foo'
    And I switch to model 'foo'
    And I deploy 'foo' from a local charm located at 'foo.charm' on base 'ubuntu@26.04'
    And I deploy 'ubuntu' on base 'ubuntu@26.04' from channel 'latest/stable'
    And I integrate 'foo:juju-info' with 'ubuntu:juju-info'
    Then all agents are 'idle' in model 'foo'
    And the workload status for app 'foo' is 'active'

  - |-
    Run the get-config action

    Given 'foo' is deployed
    When I run action 'get-config' on unit 'foo/0'
    Then the action result field 'mode' should be 'default'

  - |-
    Misconfigure the foo charm

    Given 'foo' is deployed
    And I set 'mode' for app 'foo' to 'bogus'
    Then the workload status for app 'foo' is 'blocked'
    And the workload status message for app 'foo' is 'Invalid mode: bogus'
```

Note the dependency ordering: scenario 1 deploys; scenarios 2 and 3 begin
with `Given 'foo' is deployed` to assert and rely on that state.

### Step 4 — Validate and generate

```bash
just gherkinator validate
# All 1 test plan(s) are valid.

just gherkinator generate
# -> tests/integration/features/functional_edge_tests.feature
```

Commit the generated `.feature` file together with the YAML plan.
`just gherkinator generate` renders every plan by default; to scope the
render, pass a classification flag through (for example
`just gherkinator generate --status=implemented`).

### Step 5 — Write the test module with custom steps

`tests/integration/test_edge.py`:

```python
"""BDD step definitions for foo edge tests."""

from pytest_bdd import parsers, scenarios, then
from pytest_jubilant_bdd import Context

from constants import EDGE_FEATURES

scenarios(*EDGE_FEATURES)


@then(parsers.parse("the action result field '{field}' should be '{value}'"))
def assert_action_result_field(context: Context, field: str, value: str) -> None:
    """Assert a field in the most recent action result matches the expected value."""
    task = context.action_results.peek()
    assert task.results.get(field) == value
```

Everything else — pack, deploy, integrate, run action, status assertions —
is handled by built-in steps. One custom step for the action-result field
inspection.

### Step 6 — Run and sync

```bash
just integration   # or: pytest tests/integration -v
```

`pytest-gherkinator` orders the run (edge risk first, `functional` type
first within it) and skips any `planned`/`deprecated` scenarios. Once green:

1. Verify sync: `just gherkinator diff` exits 0.
2. Commit the YAML plan and the generated `.feature` file together.

Status changes stay human-directed: every drafted plan is `implemented`,
and `planned`/`deprecated` are applied only when the user explicitly asks.

## Example 2: Polled assertion folded into a Then step

Anti-pattern (interleaved When/Then):

```gherkin
When I execute 'scontrol --json show node compute-1' on unit 'controller/0'
Then the node 'compute-1' should be registered with Slurm
```

Correct — the `Then` step runs the command itself on each poll:

```gherkin
Then the node 'compute-1' should be registered with Slurm on unit 'controller/0'
```

Custom step implementation:

```python
import json

from pytest_bdd import parsers, then
from pytest_jubilant_bdd import Context


@then(
    parsers.parse(
        "the node '{name}' should be registered with Slurm on unit '{unit}'"
    )
)
def assert_node_registered(context: Context, name: str, unit: str) -> None:
    """Assert that a Slurm node is registered, polling until it appears."""
    context.wait(
        ready=lambda ctx: _node_is_registered(ctx, name, unit),
    )


def _node_is_registered(context: Context, name: str, unit: str) -> bool:
    """Return True if the node appears in scontrol output on the unit."""
    juju = context.get_juju()
    result = juju.exec(f"scontrol --json show node {name}", unit=unit)
    data = json.loads(result.stdout)
    return bool(data.get("nodes"))
```

The `not ... should be registered` variant inverts the check. This pattern
replaces `tenacity.Retrying` loops from traditional jubilant tests.

## Example 3: SSH output field assertion

For commands whose output is `KEY=VALUE` lines (e.g. `/etc/os-release`):

```gherkin
When I ssh into unit 'apptainer/0' and I execute 'apptainer exec ubuntu.sif cat /etc/os-release'
Then the ssh output field 'VERSION_CODENAME' should be 'jammy'
```

Custom step (from `canonical/apptainer-operator`):

```python
@then(parsers.parse("the ssh output field '{field}' should be '{value}'"))
def assert_ssh_output_field(context: Context, field: str, value: str) -> None:
    """Assert a KEY=VALUE field is present in the next `juju ssh` output (LIFO order)."""
    output = context.ssh_results.pop()
    assert f"{field}={value}" in output
```

Note the `pop()` — LIFO order means the most recent `When I ssh ...` result
is consumed first when multiple ssh steps precede the assertion.

## Example 4: Multi-model test

From `canonical/sssd-operator` — the charm under test lives in one model,
its LDAP server dependency in another:

```yaml
scenarios:
  - |-
    Integrate SSSD with an LDAP server

    Given 'sssd' is deployed
    And I add model 'ldap'
    And I set 'cloudinit-userdata' for model 'ldap' to 'tests/integration/assets/openldap-cloud-init.yaml'
    And I deploy 'ubuntu' in model 'ldap' on base 'ubuntu@26.04' from channel 'latest/stable' with name 'openldap'
    And I deploy 'ldap-integrator' in model 'sssd' on base 'ubuntu@24.04' from channel 'latest/stable'
    And I configure 'ldap-integrator' with data from 'openldap'
    And I integrate 'sssd:ldap' with 'ldap-integrator:ldap'
    Then all agents are 'idle' in models 'sssd' and 'ldap'
    And the workload status for app 'sssd' is 'active'
```

The custom `Given I configure 'ldap-integrator' with data from 'openldap'`
step reaches across both models:

```python
@given("I configure 'ldap-integrator' with data from 'openldap'")
def configure_ldap_integrator(context: Context) -> None:
    """Configure `ldap-integrator` application with data from `openldap`."""
    sssd_model = context.get_juju("sssd")
    ldap_model = context.get_juju("ldap")

    # ... wait for LDAP, create secrets, configure ldap-integrator ...
```

Key points:

- `context.get_juju("<model>")` returns the `Juju` instance scoped to that
  model.
- `Then all agents are 'idle' in models 'sssd' and 'ldap'` asserts across
  both models in one step.

## Example 5: Parametrised scenario (Scenario Outline)

When the same flow must be exercised with different data:

```yaml
feature: "Config validation"
type: functional
status: implemented
risk: beta
scenarios:
  - |-
    Reject invalid modes

    Given 'foo' is deployed
    And I set 'mode' for app 'foo' to '<mode>'
    Then the workload status for app 'foo' is 'blocked'
    And the workload status message for app 'foo' is 'Invalid mode: <mode>'
examples:
  - - bogus
  - - "!!"
  - - 123
```

Generates a `Scenario Outline:` with an `Examples:` table; pytest-bdd runs
one test per row.

## Example 6: Pushing and pulling files with `scp`

Use the built-in `scp_to_unit` / `scp_from_unit` handlers instead of
hand-rolling `juju scp` calls in custom steps:

```yaml
scenarios:
  - |-
    Push a config file and pull back a log file

    Given 'foo' is deployed
    When I copy 'tests/integration/assets/config.yaml' to unit 'foo/0' at '/etc/foo/config.yaml'
    And I copy '/var/log/foo.log' from unit 'foo/0' to 'tests/integration/assets/foo.log'
    Then the pulled log file mentions the pushed config
```

Notes:

- `at '{remote_path}'` omitted → the file lands in the remote user's home
  directory.
- `to '{local_path}'` omitted → the file is written into the working
  directory using the basename of the remote path.
- The final `Then` is a custom step reading the pulled local file:

```python
@then(parsers.parse("the pulled log file mentions the pushed config"))
def assert_log_mentions_config(context: Context) -> None:
    """Assert the pulled log file references the pushed config file."""
    log = Path("tests/integration/assets/foo.log").read_text()
    assert "/etc/foo/config.yaml" in log
```

## Example 7: Cross-model integration via offers

When the charm under test must integrate with an application deployed in a
different model, use `create_offer` / `consume_offer`:

```yaml
scenarios:
  - |-
    Integrate foo with a database offered from another model

    Given I add model 'app'
    And I switch to model 'app'
    And I deploy 'foo' from a local charm
    And I add model 'data'
    And I deploy 'postgresql' in model 'data' from channel '14/stable'
    And I create offer 'db' from app 'postgresql' and endpoint 'database' in model 'data'
    And I consume offer 'admin/data.db'
    And I integrate 'foo:database' with 'db:database'
    Then all agents are 'idle' in models 'app' and 'data'
    And the workload status for app 'foo' is 'active'
```

Key points:

- The offer URL is `<controller-owner>/<model>.<offer-name>` — the offer
  named `db` created in model `data` becomes `admin/data.db`.
- `I consume offer 'admin/data.db'` has no model clause, so it consumes
  into the default model set by `Given I switch to model 'app'`. Add
  `in model '{model}'` to consume into a different model.

## Example 8: Storage lifecycle

Deploy with a storage directive, attach more storage, then remove it —
asserting attachment with the `assert_storage_attached` checkpoint:

```yaml
scenarios:
  - |-
    Deploy foo with attached storage

    Given I add model 'foo'
    And I switch to model 'foo'
    And I deploy 'foo' from a local charm with storage 'data=1G'
    Then '1' instances of storage 'data' are attached to unit 'foo/0'
  - |-
    Grow and shrink attached storage

    Given 'foo' is deployed
    And I add storage 'data' to unit 'foo/0' of size '2G' with '2' instances
    And '3' instances of storage 'data' are attached to unit 'foo/0'
    And I remove storage 'data/1' and 'data/2'
    Then '1' instances of storage 'data' are attached to unit 'foo/0'
```

Key points:

- Storage directives in `with storage '{...}'` clauses have the form
  `name=directive` (for example `'data=1G'` or `'osd-standalone=loop,2G,3'`).
- `add_storage` builds its directive as `<pool>,<count>,<size>` from the
  optional clauses; if no count is given, one instance is added.
- The checkpoint phrasing is fixed — always `'{count}' instances of storage
  ... are attached`, even for a single instance.
- The mid-scenario `And '3' instances ...` line is a checkpoint used inside
  the `Given` stanza; `remove_storage` is `Given`-only, so it must appear
  before the `Then` stanza.

## Example 9: Machine placement, mid-scenario checkpoints, and fixed waits

For machine-based (non-Kubernetes) deployments, add machines first and
target them at deploy time. Checkpoint steps can be used mid-scenario via
`And`/`But`, and `wait_for` pauses a scenario for a fixed duration:

```yaml
scenarios:
  - |-
    Deploy foo to a dedicated machine

    Given I add model 'machines'
    And I switch to model 'machines'
    And I add a machine with constraints 'mem=4G cores=2'
    And I deploy 'foo' from a local charm to machine '0'
    And all agents are 'idle'
    And the workload status for app 'foo' is 'active'
  - |-
    Reconfigure and let the charm settle

    Given 'foo' is deployed
    And I set 'mode' for app 'foo' to 'fast'
    And 'mode' for app 'foo' is set to 'fast'
    And I wait for '30' seconds
    Then the workload status for app 'foo' is 'active'
```

Key points:

- `add_machine` cannot be used with Kubernetes clouds.
- `And all agents are 'idle'` inside the `Given` stanza is a checkpoint —
  it waits for the deployment to settle before the scenario proceeds.
- `I wait for '{n}' seconds` accepts fractional values (for example
  `'2.5'`). Prefer polling checkpoints over fixed waits whenever an
  observable condition exists.
- `'mode' for app 'foo' is set to 'fast'` verifies the config change took
  effect; `is_app_config_set` is `Given`-only, so it must appear before the
  `Then` stanza.

## Example 10: Execution order and CI gating

`pytest-gherkinator` (installed alongside `pytest-jubilant-bdd`) turns the
classification tags into pytest marks, orders the run, and skips
non-implemented scenarios:

```bash
just integration                  # full suite: edge → beta → candidate → stable
pytest -m edge                    # PR gate: edge-risk scenarios only
pytest -m "edge and functional"  # narrow to a classification pair
```

To park a test that is not expected to pass yet, the human-in-the-loop
marks its plan `status: planned` — never do this on your own initiative.
`pytest-gherkinator` then skips its scenarios in every normal run; to
execute them while iterating, disable the plugin for that run:

```bash
pytest -p no:pytest-gherkinator tests/integration/test_edge.py
```
