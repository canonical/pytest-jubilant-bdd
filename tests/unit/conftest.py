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

"""Configure unit tests for ``pytest-jubilant-bdd``."""

from unittest.mock import MagicMock, patch

import pytest
from constants import MODEL_SUFFIX
from helpers import make_app_with_relation, make_status_json
from pytest_mock import MockerFixture

# Applied in ``pytest_configure`` (below) so the mock is active before any
# session fixture — notably ``context`` — is constructed. A session-scoped
# autouse fixture would race with ``context`` setup now that the plugin's
# autouse ``_reset_scenario_state`` fixture depends on ``context``.
_SECRETS_TOKEN_HEX_PATCH = patch("secrets.token_hex", return_value=MODEL_SUFFIX)


@pytest.fixture(scope="function")
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    """Mock `subprocess.run` in a test function."""
    mock = mocker.patch("subprocess.run")
    mock.return_value = MagicMock(
        stdout="stdout patched by conftest.py", stderr="stderr patched by conftest.py"
    )

    return mock


@pytest.fixture(scope="function")
def mock_status_json(mock_subprocess_run: MagicMock) -> None:
    """Configure ``mock_subprocess_run`` to return a valid status JSON.

    The default payload contains a single ``slurmctld`` app with a relation
    to ``slurmd``. Tests that need a different payload should reconfigure
    ``mock_subprocess_run.return_value.stdout`` after using this fixture.
    """
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_status_json({"slurmctld": make_app_with_relation("slurmctld", "slurmd")}),
        stderr="",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Disable Juju model teardown and mock ``secrets.token_hex`` for unit tests.

    Unit tests mock ``subprocess.run`` and never create real Juju models,
    so teardown is unnecessary and would trigger real ``juju destroy-model`` calls.

    The ``secrets.token_hex`` mock is started here (rather than via a
    session-scoped autouse fixture) so it is active before any session
    fixture — notably ``context`` — is constructed. ``Context()`` generates
    a model suffix via ``secrets.token_hex`` in its constructor, so the
    mock must be in place before that runs.
    """
    config.option.juju_bdd_no_teardown = True
    _SECRETS_TOKEN_HEX_PATCH.start()


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stop the ``secrets.token_hex`` mock after the test session."""
    _SECRETS_TOKEN_HEX_PATCH.stop()
