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

"""`pytest-jubilant-bdd` plugin module."""

__all__ = ["Context"]

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from ._constants import WORKLOAD_STATUSES
from ._context import Context
from ._errors import AppNotFoundError, CharmNotFoundError, TooManyDeployedAppsError
from ._parsers import flexible, make_list, make_dict

# ---
# `pytest` fixtures.
# ---


@pytest.fixture(scope="session")
def context() -> Context:
    """Track the testing context of a ``pytest`` session."""
    return Context()


# ---
# Gherkin step handlers.
# ---

# Given steps - Setup and context building


@given(parsers.parse("I add model '{model}'"))
def add_model(context: Context, model: str) -> None:
    """Add a new model."""
    context.models.add(model)


@given(
    flexible(
        "I deploy '{app}' "
        "[in model '{model}'] "
        "[from channel '{channel}'] "
        "[on base '{base}']"
    )
)
def deploy(
    context: Context,
    app: str,
    model: str | None,
    channel: str | None,
    base: str | None,
) -> None:
    """Deploy an application from Charmhub."""
    _deploy(context, app, model=model, channel=channel, base=base)


@given(
    flexible(
        "I deploy '{app}' from a local charm "
        "[located at '{path}'] "
        "[in model '{model}'] "
        "[on base '{base}']"
    ),
    converters={"path": lambda v: Path(v) if v is not None else v},
)
def deploy_local(
    context: Context, app: str, path: Path | None, model: str | None, base: str | None
) -> None:
    """Deploy an application from a local ``*.charm`` file."""
    if path is None:
        # Attempt to resolve the local charm path from an environment variable
        # if "located at '{path}'" isn't provided in the Gherkin step.
        env_var = app.upper().replace("-", "_") + "_CHARM_PATH"
        try:
            path = Path(os.environ[env_var])
        except KeyError:
            raise CharmNotFoundError(
                f"Charm not found: environment variable '{env_var}' is not set. "
                f"Either set the environment variable '{env_var}' to the path of "
                f"the local '*.charm' file, or provide a path in the Gherkin step "
                f"(\"I deploy '{app}' from a local charm located at '<path>'\")"
            ) from None

    if not path.is_file():
        raise CharmNotFoundError(f"Charm not found: '{path}' is not a file") from None

    _deploy(context, path.resolve(), app, model=model, base=base)


def _deploy(
    context: Context,
    /,
    charm: str | Path,
    app: str | None = None,
    *,
    model: str | None = None,
    channel: str | None = None,
    base: str | None = None,
) -> None:
    """Base function to deploy a charm."""
    juju = context.get_juju(model)

    juju.deploy(charm, app, base=base, channel=channel)


@given(parsers.parse("I integrate '{app_one}' with '{app_two}'"))
def integrate(context: Context, app_one: str, app_two: str) -> None:
    """Integrate two applications together."""
    juju = context.get_juju()

    juju.integrate(app_one, app_two)


@given(parsers.parse("model '{model}' exists"))
def model_exists(context: Context, model: str) -> None:
    """Verify that a model exists in the current testing context."""
    assert model in context.models


@given(parsers.parse("'{app_one}' is integrated with '{app_two}'"))
def is_integrated(context: Context, app_one: str, app_two: str) -> None:
    """Verify that two applications are integrated."""
    app = context.get_app(app_one)
    for integrations in app.relations.values():
        for integration in integrations:
            if integration.related_app == app_two:
                return

    raise AssertionError(f"'{app_one}' is not integrated with '{app_two}'")


@given(flexible("'{app}' is deployed [in model '{model}']"))
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


# When steps - Actions


@when(
    flexible(
        r"I run action '{action}' on %units? (?P<units>(?:'([^']+)'(?:, (?:and )?|and )?)+)% "
        "[with parameters '{params}'] "
        "[in model '{model}'] "
    ),
    converters={"units": make_list, "params": make_dict},
)
def run_action(
    context: Context,
    action: str,
    units: list[str],
    params: Mapping[str, Any] | None,
    model: str | None,
) -> None:
    """Run an action on one or more units."""
    juju = context.get_juju(model)

    for unit in units:
        result = juju.run(unit, action, params=params)
        context.action_results.push(result)


@when(
    flexible(
        "I execute '{command}' on %(?P<type_>machines?|units?) (?P<targets>(?:'([^']+)'(?:, (?:and )?|and )?)+)% "
        "[in model '{model}']"
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
        result = juju.exec(command, **{type_.rstrip("s"): target})
        context.exec_results.push(result)


# Then steps - Attestation and verification.


@then(
    parsers.re(
        r"the workload status for (?P<type_>app|unit) '(?P<target>[^']+)' is '(?P<status>%s)'"
        % "|".join(WORKLOAD_STATUSES)
    )
)
def assert_workload_status(
    context: Context, type_: str, target: str, status: str
) -> None:
    """Assert the workload status of an application or unit."""
    if type_ == "app":
        assert context.get_app(target).app_status.current == status
    else:  # target is a unit.
        assert context.get_unit(target).workload_status.current == status


@then(
    parsers.re(
        r"the workload status message for (?P<type_>app|unit) '(?P<target>[^']+)' is '(?P<message>[^']*)'"
    )
)
def assert_workload_status_message(
    context: Context, type_: str, target: str, message: str
) -> None:
    """Assert the workload status of an application or unit."""
    if type_ == "app":
        assert context.get_app(target).app_status.message == message
    else:  # target is a unit.
        assert context.get_unit(target).workload_status.message == message


# ---
# `pytest` configuration.
# ---
