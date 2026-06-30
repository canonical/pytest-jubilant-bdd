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

"""Unit tests for reusable *Then* Gherkin steps."""

from unittest.mock import MagicMock

import pytest
from constants import REUSABLE_THEN_STEP_TESTS
from helpers import make_app_with_relation, make_status_json
from pytest_bdd import scenario
from pytest_mock import MockerFixture

from pytest_jubilant_bdd import Context

# ruff: disable[SLF001]
from pytest_jubilant_bdd._main import (
    assert_all_agent_status,
    assert_workload_status,
    assert_workload_status_message,
)

# ruff: enable[SLF001]


@pytest.fixture(scope="function", autouse=True)
def _mock_time(mocker: MockerFixture) -> None:
    """Mock ``time.sleep`` to avoid real waits."""
    mocker.patch("time.sleep")  # no-op


@pytest.fixture(scope="function", autouse=True)
def _reset_models(context: Context) -> None:
    """Clear models from the context before each test.

    The ``context`` fixture is session-scoped, so models from previous
    scenarios persist across tests. This fixture clears them to avoid
    ``TooManyDeployedAppsError`` when multiple models have the same app.
    """
    context.models._data.clear()  # noqa SLF001


@pytest.fixture(scope="function")
def _mock_status_message_ready(mock_subprocess_run: MagicMock) -> None:
    """Set workload status messages to ``'ready'`` for app-level message tests."""
    app = make_app_with_relation("slurmctld", "slurmd")
    app["application-status"] = {"current": "active", "message": "ready"}
    app["units"]["slurmctld/0"]["workload-status"] = {
        "current": "active",
        "message": "ready",
    }
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_status_json({"slurmctld": app}),
        stderr="",
    )


@pytest.fixture(scope="function")
def _mock_status_message_installing(mock_subprocess_run: MagicMock) -> None:
    """Set workload status messages to ``'installing agent'`` for unit-level message tests."""
    app = make_app_with_relation("slurmctld", "slurmd")
    app["units"]["slurmctld/0"]["workload-status"] = {
        "current": "active",
        "message": "installing agent",
    }
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_status_json({"slurmctld": app}),
        stderr="",
    )


class TestAssertAllAgentStatus:
    """Test the ``assert_all_agent_status`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents are idle")
    def test_required(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with only the required clause.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents idle in multiple models")
    def test_with_optionals(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with the ``in models`` optional clause.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising the optional is sufficient.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    def test_raises_when_agent_not_idle(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_all_agent_status`` times out when the agent status is not ``'idle'``.

        Notes:
            This error path is tested by calling the handler directly rather
            than via ``@scenario`` because ``@scenario`` runs the Gherkin steps
            before the test body, so exceptions raised during step execution
            cannot be caught with ``pytest.raises``.
        """
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_all_agent_status(context, "lost", [])


class TestAssertWorkloadStatus:
    """Test the ``assert_workload_status`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for app")
    def test_for_app(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_workload_status`` for an application.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for unit")
    def test_for_unit(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_workload_status`` for a unit.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    def test_raises_when_status_not_match_app(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_workload_status`` times out when the app workload status doesn't match."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_workload_status(context, "app", "slurmctld", "maintenance")

    def test_raises_when_status_not_match_unit(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_workload_status`` times out when the unit workload status doesn't match."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_workload_status(context, "unit", "slurmctld/0", "waiting")


class TestAssertWorkloadStatusMessage:
    """Test the ``assert_workload_status_message`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status message for app")
    def test_for_app(mock_subprocess_run: MagicMock, _mock_status_message_ready: None) -> None:
        """Test ``assert_workload_status_message`` for an application.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status message for unit")
    def test_for_unit(
        mock_subprocess_run: MagicMock,
        _mock_status_message_installing: None,
    ) -> None:
        """Test ``assert_workload_status_message`` for a unit.

        No assertion is needed: the handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    def test_raises_when_message_not_match_app(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_workload_status_message`` times out when the app message doesn't match."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_workload_status_message(context, "app", "slurmctld", "wrong")

    def test_raises_when_message_not_match_unit(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_workload_status_message`` times out when the unit message doesn't match."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_workload_status_message(context, "unit", "slurmctld/0", "wrong")
