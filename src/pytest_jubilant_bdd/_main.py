#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""``pytest-jubilant-bdd`` plugin module."""

__all__ = ["Context"]

import logging
import os
import subprocess
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

import pytest
from jubilant import TaskError
from pytest_bdd import given, parsers, then, when

from ._assertions import assertions
from ._constants import (
    AGENT_STATUS_CAPTURE_GROUP,
    DEFAULT_WAIT_TIMEOUT,
    NO_TEARDOWN_FLAG_NAME,
    OPTIONAL_MODEL_CLAUSE,
    OPTIONAL_TIMEOUT_CLAUSE,
    WAIT_TIMEOUT_FLAG_NAME,
    WORKLOAD_STATUS_CAPTURE_GROUP,
    AgentStatus,
    WorkloadStatus,
)
from ._context import Context
from ._parsers import flexible, make_dict, make_list
from .errors import AppNotFoundError, TooManyDeployedAppsError

logger = logging.getLogger("pytest-jubilant-bdd")

# ---
# `pytest` hooks.
# ---


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ``pytest-jubilant-bdd``-specific command-line options.

    Args:
        parser: The :class:`pytest.Parser` object for this ``pytest-jubilant-bdd`` session.

    Notes:
        - Upstream ``pytest_configure`` hook documentation:
          https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_addoption
    """
    group = parser.getgroup("jubilant-bdd")
    group.addoption(
        NO_TEARDOWN_FLAG_NAME,
        action="store_true",
        default=False,
        help="Skip teardown of model(s) after BDD tests complete.",
    )
    group.addoption(
        WAIT_TIMEOUT_FLAG_NAME,
        action="store",
        type=float,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Set the wait timeout (in seconds) for the BDD testing context.",
    )


# ---
# `pytest` fixtures.
# ---


@pytest.fixture(scope="session")
def context(request: pytest.FixtureRequest) -> Iterator[Context]:
    """Track the testing context of a ``pytest`` session."""
    context = Context(wait_timeout=cast(float, request.config.getoption(WAIT_TIMEOUT_FLAG_NAME)))

    yield context

    if not request.config.getoption(NO_TEARDOWN_FLAG_NAME):
        context.models.destroy(destroy_storage=True, force=True)


# ---
# Gherkin step handlers.
# ---


# Given steps - Setup and context building


@given(parsers.parse("I add model '{model}'"))
def add_model(context: Context, model: str) -> None:
    """Add a new model."""
    context.models.add(model)


@given(
    flexible("I add '{num_units}' %units?% to app '{app}' " + OPTIONAL_MODEL_CLAUSE),
    converters={"num_units": int},
)
def add_unit(context: Context, num_units: int, app: str, model: str | None) -> None:
    """Add units to a deployed application."""
    juju = context.get_juju(model)

    juju.add_unit(app, num_units=num_units)


@given(
    flexible(
        r"%I add (?:'(?P<num_machines>\d+)' |a )machines?%"
        "[to '{target}'] "
        "[%(?:that )?uses?% base '{base}'] "
        "[with constraints '{constraints}'] "
        "[with disks '{disks}'] " + OPTIONAL_MODEL_CLAUSE
    ),
    converters={
        "num_machines": lambda v: int(v) if v is not None else 1,
        "constraints": make_dict,
    },
)
def add_machine(
    context: Context,
    num_machines: int = 1,
    target: str | None = None,
    base: str | None = None,
    constraints: Mapping[str, Any] | None = None,
    disks: str | None = None,
    model: str | None = None,
) -> None:
    """Add one or more machines to a Juju model.

    Notes:
        - This step handler cannot be used with Kubernetes clouds.
    """
    juju = context.get_juju(model)

    juju.add_machine(
        target,
        base=base,
        constraints=constraints or None,
        disks=disks,
        num_machines=num_machines,
    )


@given(
    flexible(
        "I add storage '{storage}' to unit '{unit}' "
        "[from pool '{pool}'] "
        "[of size '{size}'] "
        "[with '{count}' %instances?%] " + OPTIONAL_MODEL_CLAUSE
    ),
    converters={"count": lambda v: int(v) if v is not None else 1},
)
def add_storage(
    context: Context,
    storage: str,
    unit: str,
    pool: str | None,
    size: str | None,
    count: int,
    model: str | None,
) -> None:
    """Add one or more storage instances to a deployed unit.

    Notes:
        - The storage directive is built from the optional clauses in the order
          recommended by the Juju CLI: ``<pool>,<count>,<size>``. If no count is
          provided, one storage instance is added.
    """
    juju = context.get_juju(model)

    parts: list[str] = []
    if pool is not None:
        parts.append(pool)
    parts.append(str(count))
    if size is not None:
        parts.append(size)

    juju.cli("add-storage", unit, f"{storage}={','.join(parts)}")


@given(
    flexible(
        r"I remove %units? (?P<units>(?:'([^']+)'(?:, (?:and )?|\s+and )?)+)%"
        + OPTIONAL_MODEL_CLAUSE
    ),
    converters={"units": make_list},
)
def remove_unit(context: Context, units: list[str], model: str | None) -> None:
    """Remove one or more units from a deployed application."""
    juju = context.get_juju(model)

    juju.remove_unit(*units)


@given(
    flexible(
        r"I remove %storage (?P<storages>(?:'([^']+)'(?:, (?:and )?|\s+and )?)+)%"
        + OPTIONAL_MODEL_CLAUSE
    ),
    converters={"storages": make_list},
)
def remove_storage(context: Context, storages: list[str], model: str | None) -> None:
    """Remove one or more storage instances from a Juju model."""
    juju = context.get_juju(model)

    juju.cli("remove-storage", *storages)


@given(
    flexible("I pack %an?% '{app}' charm [from project directory '{project_dir}']"),
)
def pack_charm(context: Context, app: str, project_dir: str | None) -> None:
    """Pack a charm from a project directory using ``charmcraft``.

    If the ``<APP>_CHARM_PATH`` environment variable is set, ``charmcraft
    pack`` is skipped. This allows the ``deploy_local`` step handler to use
    a pre-built ``*.charm`` file instead.

    If ``project_dir`` is not provided, then the current working directory
    is used instead.
    """
    env_var = app.upper().replace("-", "_") + "_CHARM_PATH"
    if env_var in os.environ:
        logger.info("skipping charmcraft pack: '%s' is set to '%s'", env_var, os.environ[env_var])
        return

    project = Path(project_dir) if project_dir else Path.cwd()
    try:
        subprocess.run(
            ["charmcraft", "-v", "pack"],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise FileNotFoundError("'charmcraft' is not installed or not found on PATH") from None

    charms = list(project.glob(f"{app}*.charm"))
    if not charms:
        raise FileNotFoundError(f"No .charm file found for '{app}' in '{project}'")

    charms[0].rename(f"{app}.charm")


@given(
    flexible(
        "I deploy '{app}' "
        "[from channel '{channel}'] "
        "[on base '{base}'] "
        "[with '{num_units}' %units?%] "
        "[with name '{name}'] "
        "[with %constraints?% '{constraints}'] " + OPTIONAL_MODEL_CLAUSE
    ),
    converters={
        "num_units": lambda v: int(v) if v is not None else 1,
        "constraints": make_dict,
    },
)
def deploy(
    context: Context,
    app: str,
    model: str | None,
    channel: str | None,
    base: str | None,
    num_units: int,
    name: str | None,
    constraints: Mapping[str, Any],
) -> None:
    """Deploy an application from Charmhub."""
    _deploy(
        context,
        app,
        model=model,
        channel=channel,
        base=base,
        num_units=num_units,
        name=name,
        constraints=constraints,
    )


@given(
    flexible(
        "I deploy '{app}' from a local charm "
        "[located at '{path}'] "
        "[on base '{base}'] "
        "[with '{num_units}' %units?%] "
        "[with name '{name}'] "
        "[with %constraints?% '{constraints}'] " + OPTIONAL_MODEL_CLAUSE
    ),
    converters={
        "path": lambda v: Path(v) if v is not None else v,
        "num_units": lambda v: int(v) if v is not None else 1,
        "constraints": make_dict,
    },
)
def deploy_local(
    context: Context,
    app: str,
    path: Path | None,
    model: str | None,
    base: str | None,
    num_units: int,
    name: str | None,
    constraints: Mapping[str, Any],
) -> None:
    """Deploy an application from a local ``*.charm`` file."""
    if path is None:
        # Allow the charm path to be resolved from an environment variable
        # if "located at '{path}'" isn't provided in the Gherkin step.
        env_var = app.upper().replace("-", "_") + "_CHARM_PATH"
        try:
            path = Path(os.environ[env_var])
        except KeyError:
            raise FileNotFoundError(
                f"Charm not found: environment variable '{env_var}' is not set. "
                f"Either set the environment variable '{env_var}' to the path of "
                f"the local '*.charm' file, or provide a path in the Gherkin step "
                f"(\"I deploy '{app}' from a local charm located at '<path>'\")"
            ) from None

    if not path.is_file():
        raise FileNotFoundError(f"Charm not found: '{path}' is not a file") from None

    _deploy(
        context,
        path.resolve(),
        app,
        model=model,
        base=base,
        num_units=num_units,
        name=name,
        constraints=constraints,
    )


def _deploy(
    context: Context,
    /,
    charm: str | Path,
    app: str | None = None,
    *,
    model: str | None = None,
    channel: str | None = None,
    base: str | None = None,
    name: str | None = None,
    num_units: int = 1,
    constraints: Mapping[str, Any] | None = None,
) -> None:
    """Deploy an application."""
    juju = context.get_juju(model)

    juju.deploy(
        charm,
        name or app,
        base=base,
        channel=channel,
        num_units=num_units,
        constraints=constraints,
    )


@given(
    flexible(
        "I create offer '{name}' "
        "from app '{app}' "
        "and endpoint '{endpoint}' " + OPTIONAL_MODEL_CLAUSE
    )
)
def create_offer(context: Context, name: str, app: str, endpoint: str, model: str | None) -> None:
    """Create a cross-model offer from a deployed application's endpoint."""
    juju = context.get_juju(model)

    juju.offer(app, endpoint=endpoint, name=name)


@given(flexible("I consume offer '{offer}' [as '{alias}'] " + OPTIONAL_MODEL_CLAUSE))
def consume_offer(context: Context, offer: str, alias: str | None, model: str | None) -> None:
    """Consume a remote offer into a model."""
    juju = context.get_juju(model)

    juju.consume(offer, alias)


@given(flexible("I integrate '{app_one}' with '{app_two}' " + OPTIONAL_MODEL_CLAUSE))
def integrate(context: Context, app_one: str, app_two: str, model: str | None) -> None:
    """Integrate two applications together."""
    juju = context.get_juju(model)

    juju.integrate(app_one, app_two)


@given(flexible("I disintegrate '{app_one}' and '{app_two}' " + OPTIONAL_MODEL_CLAUSE))
def disintegrate(context: Context, app_one: str, app_two: str, model: str | None) -> None:
    """Disintegrate two applications (remove the relation between them)."""
    juju = context.get_juju(model)

    juju.remove_relation(app_one, app_two)


@given(parsers.parse("model '{model}' exists"))
def model_exists(context: Context, model: str) -> None:
    """Verify that a model exists in the current testing context."""
    assert model in context.models


@given(flexible("'{option}' for app '{app}' is set to '{value}' " + OPTIONAL_MODEL_CLAUSE))
def is_app_config_set(
    context: Context,
    option: str,
    app: str,
    value: str,
    model: str | None,
) -> None:
    """Verify that a configuration option for a deployed application is set to a value."""
    juju = context.get_juju(model)
    config = juju.config(app)
    actual = config.get(option)
    if isinstance(actual, bool):
        matches = str(actual).lower() == value.lower()
    else:
        matches = str(actual) == value
    if not matches:
        message = f"Option '{option}' for app '{app}' is not set to '{value}'"
        if model:
            message += f" in model '{model}'"
        raise AssertionError(message)


@given(flexible("'{app_one}' is integrated with '{app_two}' " + OPTIONAL_MODEL_CLAUSE))
def is_integrated(context: Context, app_one: str, app_two: str, model: str | None) -> None:
    """Verify that two applications are integrated."""
    try:
        app = context.get_app(app_one, model=model)
    except AppNotFoundError:
        message = f"'{app_one}' is not deployed"
        if model:
            message += f" in model '{model}'"
        raise AssertionError(message)
    except TooManyDeployedAppsError:
        raise AssertionError(
            f"More than one app is named '{app_one}'. Provide the model name in the "
            f"Gherkin step to check for the integration of a specific app instance. "
            f"(\"'{app_one}' is integrated with '{app_two}' in model '<model>'\")"
        )

    for integrations in app.relations.values():
        for integration in integrations:
            if integration.related_app == app_two:
                return

    message = f"'{app_one}' is not integrated with '{app_two}'"
    if model:
        message += f" in model '{model}'"
    raise AssertionError(message)


@given(flexible("'{app}' is deployed " + OPTIONAL_MODEL_CLAUSE))
def is_deployed(context: Context, app: str, model: str | None) -> None:
    """Verify that an application is deployed."""
    try:
        context.get_app(app, model=model)
    except AppNotFoundError:
        message = f"'{app}' is not deployed"
        if model:
            message += f" in model '{model}'"
        raise AssertionError(message)
    except TooManyDeployedAppsError:
        raise AssertionError(
            f"More than one app is named '{app}'. Provide the model name in the "
            f"Gherkin step to check for the existence of specific app instance. "
            f"(\"'{app}' is deployed in model '<model>'\")"
        )


@given(flexible("I reset '{option}' for app '{app}' " + OPTIONAL_MODEL_CLAUSE))
def reset_app_config(
    context: Context,
    option: str,
    app: str,
    model: str | None,
) -> None:
    """Reset a configuration option for a deployed application to its default."""
    juju = context.get_juju(model)

    juju.config(app, reset=option)


@given(flexible("I set '{option}' for app '{app}' to '{value}' " + OPTIONAL_MODEL_CLAUSE))
def set_app_config(
    context: Context,
    option: str,
    app: str,
    value: str,
    model: str | None,
) -> None:
    """Set a configuration option for a deployed application."""
    juju = context.get_juju(model)

    juju.config(app, values={option: value})


@given(parsers.parse("I set '{option}' for model '{model}' to '{value}'"))
def set_model_config(context: Context, option: str, model: str, value: str) -> None:
    """Set a configuration option for a Juju model."""
    if option == "cloudinit-userdata":
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(f"Cloud-init user data file not found: '{value}'") from None

        value = path.read_text()

    juju = context.get_juju(model)
    juju.model_config({option: value})


@given(parsers.parse("I reset '{option}' for model '{model}'"))
def reset_model_config(context: Context, option: str, model: str) -> None:
    """Reset a configuration option for a Juju model to its default."""
    juju = context.get_juju(model)
    juju.model_config(reset=option)


@given(parsers.parse("I switch to model '{model}'"))
def switch_model(context: Context, model: str) -> None:
    """Switch the default model for subsequent step handlers.

    All following steps that accept an optional model parameter will use
    this model when no explicit model is provided.
    """
    context.default_model = model


# When steps - Actions


@when(
    flexible(
        r"I run action '{action}' on %units? (?P<units>(?:'([^']+)'(?:, (?:and )?|\s+and )?)+)%"
        "[with parameters '{params}'] " + OPTIONAL_MODEL_CLAUSE
    ),
    converters={"units": make_list, "params": make_dict},
)
def run_action(
    context: Context,
    action: str,
    units: list[str],
    params: Mapping[str, Any],
    model: str | None,
) -> None:
    """Run an action on one or more units."""
    juju = context.get_juju(model)

    for unit in units:
        # `Juju.run` performs a `NoneType` check on `params`, but not a zero-value check.
        # Set `params` to `None` if the Gherkin step doesn't include action parameters to
        # avoid the creation of a superfluous temp file.
        try:
            result = juju.run(unit, action, params=params if params else None)
        except TaskError as e:
            result = e.task

        context.action_results.push(result)


@when(
    flexible(
        r"I execute '{command}' on %(?P<type_>machines?|units?) (?P<targets>(?:'([^']+)'(?:, (?:and )?|\s+and )?)+)%"
        + OPTIONAL_MODEL_CLAUSE
    ),
    converters={"targets": make_list},
)
def run_exec(
    context: Context,
    command: str,
    type_: str,
    targets: list[str | int],
    model: str | None,
) -> None:
    """Run remote commands on provided targets."""
    juju = context.get_juju(model)

    for target in targets:
        try:
            match type_.rstrip("s"):
                case "machine":
                    result = juju.exec(command, machine=target)
                case "unit":
                    result = juju.exec(command, unit=cast(str, target))
        except TaskError as e:
            result = e.task

        context.exec_results.push(result)  # type: ignore[reportPossiblyUnboundVariable] # noqa
        # `result` cannot be unbound because this step handler will always match `type_`
        # to "machine" or "unit". Otherwise, this handler will not match the Gherkin step.


@when(
    flexible(
        r"I ssh into %(?P<type_>machine|unit) '(?P<target>[^']+)'% "
        r"and I execute '{command}'" + OPTIONAL_MODEL_CLAUSE
    ),
)
def run_ssh(
    context: Context,
    type_: str,
    target: str,
    command: str,
    model: str | None,
) -> None:
    """SSH into a machine or unit and execute a command."""
    juju = context.get_juju(model)

    match type_:
        case "machine":
            result = juju.ssh(int(target), command)
        case "unit":
            result = juju.ssh(target, command)

    context.ssh_results.push(result)  # type: ignore[reportPossiblyUnboundVariable] # noqa
    # `result` cannot be unbound because this step handler will always match `type_`
    # to "machine" or "unit". Otherwise, this handler will not match the Gherkin step.


# Checkpoint steps - Attestation and verification.
#
# Each handler below is registered as a `given`, `when`, and `then` step so
# that checkpoint-style assertions can be used in any stanza of a scenario
# through the `And` and `But` conjunctions.


_ALL_AGENT_STATUS_STEP = (
    rf"all agents are %'{AGENT_STATUS_CAPTURE_GROUP}'% "
    r"[in %models? (?P<models>(?:'([^']+)'(?:, (?:and )?|\s+and )?)+)%] " + OPTIONAL_TIMEOUT_CLAUSE
)
_ALL_AGENT_STATUS_CONVERTERS = {
    "models": make_list,
    "timeout": lambda v: float(v) if v is not None else None,
}


@given(flexible(_ALL_AGENT_STATUS_STEP), converters=_ALL_AGENT_STATUS_CONVERTERS)
@when(flexible(_ALL_AGENT_STATUS_STEP), converters=_ALL_AGENT_STATUS_CONVERTERS)
@then(flexible(_ALL_AGENT_STATUS_STEP), converters=_ALL_AGENT_STATUS_CONVERTERS)
def assert_all_agent_status(
    context: Context, status: AgentStatus, models: list[str], timeout: float | None = None
) -> None:
    """Assert the status for all agents.

    If no model names are provided, then the status of all agents in the current testing context
    will be validated.

    Notes:
        - If a timeout is provided, it overrides the global ``--juju-bdd-wait-timeout``
          for this step.
    """
    context.wait(
        ready=lambda ctx: assertions.model.all_agent_statuses_are(ctx, *models, expected=status),
        timeout=timeout,
    )


_WORKLOAD_STATUS_STEP = (
    r"%the workload status for (?P<type_>app|unit) '(?P<target>[^']+)'%"
    rf" is %'{WORKLOAD_STATUS_CAPTURE_GROUP}'% " + OPTIONAL_TIMEOUT_CLAUSE
)
_WORKLOAD_STATUS_CONVERTERS = {"timeout": lambda v: float(v) if v is not None else None}


@given(flexible(_WORKLOAD_STATUS_STEP), converters=_WORKLOAD_STATUS_CONVERTERS)
@when(flexible(_WORKLOAD_STATUS_STEP), converters=_WORKLOAD_STATUS_CONVERTERS)
@then(flexible(_WORKLOAD_STATUS_STEP), converters=_WORKLOAD_STATUS_CONVERTERS)
def assert_workload_status(
    context: Context, type_: str, target: str, status: WorkloadStatus, timeout: float | None = None
) -> None:
    """Assert the workload status of an application or unit.

    Notes:
        - If a timeout is provided, it overrides the global ``--juju-bdd-wait-timeout``
          for this step.
    """
    match type_:
        case "app":
            context.wait(
                ready=lambda ctx: assertions.app.all_unit_statuses_are(
                    ctx, target, expected=status
                ),
                timeout=timeout,
            )
        case "unit":
            context.wait(
                ready=lambda ctx: assertions.unit.all_statuses_are(ctx, target, expected=status),
                timeout=timeout,
            )


_WORKLOAD_STATUS_MESSAGE_STEP = (
    r"%the workload status message for (?P<type_>app|unit) '(?P<target>[^']+)'%"
    r" is %'(?P<message>[^']*)'% " + OPTIONAL_TIMEOUT_CLAUSE
)
_WORKLOAD_STATUS_MESSAGE_CONVERTERS = {"timeout": lambda v: float(v) if v is not None else None}


@given(flexible(_WORKLOAD_STATUS_MESSAGE_STEP), converters=_WORKLOAD_STATUS_MESSAGE_CONVERTERS)
@when(flexible(_WORKLOAD_STATUS_MESSAGE_STEP), converters=_WORKLOAD_STATUS_MESSAGE_CONVERTERS)
@then(flexible(_WORKLOAD_STATUS_MESSAGE_STEP), converters=_WORKLOAD_STATUS_MESSAGE_CONVERTERS)
def assert_workload_status_message(
    context: Context, type_: str, target: str, message: str, timeout: float | None = None
) -> None:
    """Assert the workload status message of an application or unit.

    Notes:
        - If a timeout is provided, it overrides the global ``--juju-bdd-wait-timeout``
          for this step.
    """
    match type_:
        case "app":
            context.wait(
                ready=lambda ctx: assertions.app.all_unit_status_messages_are(
                    ctx, target, expected=message
                ),
                timeout=timeout,
            )
        case "unit":
            context.wait(
                ready=lambda ctx: assertions.unit.all_status_messages_are(
                    ctx, target, expected=message
                ),
                timeout=timeout,
            )


_STORAGE_ATTACHED_STEP = (
    r"%'(?P<count>\d+)' instances of storage '(?P<storage>[^']+)'"
    r" are attached to unit '(?P<unit>[^']+)'% "
    + OPTIONAL_MODEL_CLAUSE
    + " "
    + OPTIONAL_TIMEOUT_CLAUSE
)
_STORAGE_ATTACHED_CONVERTERS = {
    "count": int,
    "timeout": lambda v: float(v) if v is not None else None,
}


@given(flexible(_STORAGE_ATTACHED_STEP), converters=_STORAGE_ATTACHED_CONVERTERS)
@when(flexible(_STORAGE_ATTACHED_STEP), converters=_STORAGE_ATTACHED_CONVERTERS)
@then(flexible(_STORAGE_ATTACHED_STEP), converters=_STORAGE_ATTACHED_CONVERTERS)
def assert_storage_attached(
    context: Context,
    count: int,
    storage: str,
    unit: str,
    model: str | None,
    timeout: float | None = None,
) -> None:
    """Assert that a number of storage instances are attached to a unit.

    Notes:
        - If a timeout is provided, it overrides the global ``--juju-bdd-wait-timeout``
          for this step.
    """
    context.wait(
        ready=lambda ctx: assertions.storage.instances_are_attached(
            ctx, storage, unit, count=count, model=model
        ),
        timeout=timeout,
    )
