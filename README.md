# pytest-jubilant-bdd

![GitHub License](https://img.shields.io/github/license/canonical/pytest-jubilant-bdd)
[![Matrix](https://img.shields.io/matrix/ubuntu-hpc%3Amatrix.org?logo=matrix&label=ubuntu-hpc)](https://matrix.to/#/#hpc:ubuntu.com)

A pytest plugin providing reusable Gherkin step handlers for
behavior-driven testing of Juju charmed operators.

pytest-jubilant-bdd is a collection of various utilities that make it easier
for you and your friends to write behavior-driven tests for Juju charmed
operators. The plugin provides a curated set of reusable Gherkin step handlers
built on top of [`jubilant`](https://github.com/canonical/jubilant) and
[`pytest-bdd`](https://pytest-bdd.readthedocs.io/), so you can focus on the
behavior of your charms instead of the boilerplate of driving the Juju
lifecycle from your tests. Current reusable steps shipped in the
pytest-jubilant-bdd package include:

* `add_machine`: A `given` step handler for adding one or more machines to a
  Juju model.
* `add_model`: A `given` step handler for adding a new Juju model to the
  testing context.
* `add_storage`: A `given` step handler for adding storage to a deployed
  unit, with optional storage pool, size, and count clauses.
* `add_unit`: A `given` step handler for adding units to a deployed
  application.
* `deploy`: A `given` step handler for deploying a charm from Charmhub.
* `deploy_local`: A `given` step handler for deploying a local `.charm` file
  onto a Juju model.
* `disintegrate`: A `given` step handler for removing the integration
  between two Juju applications.
* `integrate`: A `given` step handler for integrating two Juju applications.
* `model_exists`: A `given` step handler for asserting that a Juju model
  currently exists.
* `pack_charm`: A `given` step handler for packing a charm from a
  project directory using ``charmcraft``. Skips packing when the
  ``<APP>_CHARM_PATH`` environment variable is already set.
* `remove_unit`: A `given` step handler for removing one or more units
  from a deployed application.
* `remove_storage`: A `given` step handler for removing one or more storage
  instances from a Juju model.
* `is_app_config_set`: A `given` step handler for verifying that a
  configuration option on a deployed application is set to a value.
* `is_integrated`: A `given` step handler for asserting that two applications
  are currently integrated.
* `is_deployed`: A `given` step handler for asserting that an application is
  currently deployed on a Juju model.
* `reset_app_config`: A `given` step handler for resetting a configuration
  option on a deployed application to its default.
* `reset_model_config`: A `given` step handler for resetting a model
  configuration option to its default.
* `set_app_config`: A `given` step handler for setting a configuration option
  on a deployed application.
* `set_model_config`: A `given` step handler for setting a configuration
  option on a Juju model.
* `switch_model`: A `given` step handler for switching the default model
  that subsequent step handlers operate on.
* `run_action`: A `when` step handler for running a Juju action on one or
  more units.
* `run_exec`: A `when` step handler for executing a command on one or more
  machines or units.
* `run_ssh`: A `when` step handler for SSHing into a machine or unit and
  executing a command.
* `assert_all_agent_status`: A checkpoint step handler for asserting the
  status of all agents in one or more models, with an optional
  `within '{timeout}' seconds` clause to override the global
  `--juju-bdd-wait-timeout`.
* `assert_storage_attached`: A checkpoint step handler for asserting that a
  number of storage instances are attached to a unit, with an optional
  `within '{timeout}' seconds` clause to override the global
  `--juju-bdd-wait-timeout`.
* `assert_workload_status`: A checkpoint step handler for asserting the
  workload status of a deployed application, with an optional
  `within '{timeout}' seconds` clause to override the global
  `--juju-bdd-wait-timeout`.
* `assert_workload_status_message`: A checkpoint step handler for asserting
  the message attached to a workload status, with an optional
  `within '{timeout}' seconds` clause to override the global
  `--juju-bdd-wait-timeout`.

Checkpoint assertions are registered for `given`, `when`, and `then` steps
alike, so they can be used as checkpoints in any stanza of a scenario through
the `And`/`But` conjunctions. For example, `Given I deploy 'slurmctld'`
followed by `And all agents are 'idle'` waits for the deployment to settle
before proceeding to the next step.

For more information on how to use or contribute to pytest-jubilant-bdd,
check out the [Development](#-development) section below 👇

## 🤔 What's next?

If you want to learn more about all the things you can do with
pytest-jubilant-bdd, here are some further resources for you to explore:

* [Open an issue](https://github.com/canonical/pytest-jubilant-bdd/issues/new?title=ISSUE+TITLE&body=*Please+describe+your+issue*)

## 🛠️ Development

The project uses [just](https://github.com/casey/just) and [uv](https://github.com/astral-sh/uv)
for development, which provides some useful commands that will help you while hacking on
pytest-jubilant-bdd:

```shell
just fmt          # Apply formatting standards to code
just lint         # Check code against coding style standards
just typecheck    # Run static type checks
just unit         # Run unit tests
```

If you're interested in contributing your work to pytest-jubilant-bdd,
take a look at our contributing guidelines for further details.

## 🤝 Project and community

pytest-jubilant-bdd is a project of the [Ubuntu High-Performance Computing community](https://ubuntu.com/community/governance/teams/hpc).
Interested in contributing bug fixes, new step handlers, documentation, or feedback? Want to join the Ubuntu HPC community? You’ve come to the right place 🤩

Here’s some links to help you get started with joining the community:

* [Ubuntu Code of Conduct](https://ubuntu.com/community/ethos/code-of-conduct)
* [Join the conversation on Matrix](https://matrix.to/#/#hpc:ubuntu.com)
* [Get the latest news on Discourse](https://discourse.ubuntu.com/c/hpc/151)

## 📋 License

pytest-jubilant-bdd is free software, distributed under the Apache License, v2.0.
See the [LICENSE](./LICENSE) file for further details.
