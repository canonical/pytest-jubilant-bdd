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
from helpers import (
    make_app_with_relation,
    make_status_json,
    make_storage_instance,
    make_storage_json,
)
from pytest_bdd import scenario
from pytest_mock import MockerFixture

from pytest_jubilant_bdd import Context

# ruff: disable[SLF001]
from pytest_jubilant_bdd._main import (
    assert_all_agent_status,
    assert_storage_attached,
    assert_workload_status,
    assert_workload_status_message,
    wait_for,
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


@pytest.fixture(scope="function")
def _mock_storage_attached(mock_subprocess_run: MagicMock) -> None:
    """Configure ``mock_subprocess_run`` to return a storage JSON payload.

    The default payload contains three attached ``ost`` instances, matching
    the storage scenarios in ``then.feature``.
    """
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_storage_json(),
        stderr="",
    )


class TestAssertAllAgentStatus:
    """Test the ``assert_all_agent_status`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents are idle")
    def test_required(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with only the required clause.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents idle in multiple models")
    def test_with_multiple_models(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with the ``in models`` optional clause.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents idle in two models without comma")
    def test_without_comma(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with comma-free ``and`` list syntax.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "All agents idle with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_all_agent_status`` with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    def test_custom_timeout_is_passed_to_wait(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """A custom ``within '{timeout}' seconds`` value overrides the global wait timeout."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="after 90"):
            assert_all_agent_status(context, "lost", [], timeout=90.0)

    def test_raises_when_agent_not_idle(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """``assert_all_agent_status`` times out when the agent status is not ``'idle'``."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_all_agent_status(context, "lost", [])


class TestAssertWorkloadStatus:
    """Test the ``assert_workload_status`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for app")
    def test_required(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_workload_status`` with only the required clause.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for unit")
    def test_for_unit(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_workload_status`` for a unit.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
        assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for app with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``assert_workload_status`` with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status for unit with all optionals")
    def test_for_unit_with_optionals(
        mock_subprocess_run: MagicMock, mock_status_json: None
    ) -> None:
        """Test ``assert_workload_status`` for a unit with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    def test_custom_timeout_is_passed_to_wait(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """A custom ``within '{timeout}' seconds`` value overrides the global wait timeout."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="after 90"):
            assert_workload_status(context, "app", "slurmctld", "maintenance", timeout=90.0)

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
    def test_required(mock_subprocess_run: MagicMock, _mock_status_message_ready: None) -> None:
        """Test ``assert_workload_status_message`` with only the required clause.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status message for unit")
    def test_for_unit(
        mock_subprocess_run: MagicMock,
        _mock_status_message_installing: None,
    ) -> None:
        """Test ``assert_workload_status_message`` for a unit.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status message for app with all optionals")
    def test_with_optionals(
        mock_subprocess_run: MagicMock,
        _mock_status_message_ready: None,
    ) -> None:
        """Test ``assert_workload_status_message`` with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Workload status message for unit with all optionals")
    def test_for_unit_with_optionals(
        mock_subprocess_run: MagicMock,
        _mock_status_message_installing: None,
    ) -> None:
        """Test ``assert_workload_status_message`` for a unit with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    def test_custom_timeout_is_passed_to_wait(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
        mocker: MockerFixture,
    ) -> None:
        """A custom ``within '{timeout}' seconds`` value overrides the global wait timeout."""
        context.models.add("test")
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="after 90"):
            assert_workload_status_message(context, "app", "slurmctld", "wrong", timeout=90.0)

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


class TestAssertStorageAttached:
    """Test the ``assert_storage_attached`` *Then* step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Storage instances are attached")
    def test_required(mock_subprocess_run: MagicMock, _mock_storage_attached: None) -> None:
        """Test ``assert_storage_attached`` with only the required clause.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Storage instances are attached with all optionals")
    def test_with_optionals(
        mock_subprocess_run: MagicMock,
        _mock_storage_attached: None,
    ) -> None:
        """Test ``assert_storage_attached`` with all optional clauses.

        Notes:
            - No assertion is needed. The handler raises ``TimeoutError`` if the
              assertion fails. Reaching this point means the assertion passed.
        """

    def test_raises_when_storage_not_attached(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """``assert_storage_attached`` times out when not enough instances are attached."""
        # Each entry covers a different non-matching case in `instances_are_attached`:
        # a different storage label, a pending instance, an instance with no
        # attachments, and an instance attached to a different unit.
        instances = {
            "mgt/0": make_storage_instance(unit="lustre-server/1"),
            "ost/1": make_storage_instance(unit="lustre-server/1", status="pending"),
            "ost/2": {k: v for k, v in make_storage_instance().items() if k != "attachments"},
            "ost/3": make_storage_instance(unit="other/0"),
        }
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_storage_json(instances),
            stderr="",
        )
        mocker.patch("time.monotonic", side_effect=[0.0, 0.1, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_storage_attached(context, 3, "ost", "lustre-server/1", None)

    def test_handles_empty_storage_output(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """``assert_storage_attached`` handles ``juju storage`` returning no output."""
        # `juju storage` prints nothing when the model has no storage yet, which
        # is the case on the first poll after `juju add-storage`.
        mock_subprocess_run.return_value = MagicMock(stdout="", stderr="")
        mocker.patch("time.monotonic", side_effect=[0.0, 0.1, 999.0])

        with pytest.raises(TimeoutError, match="Wait timed out"):
            assert_storage_attached(context, 1, "ost", "lustre-server/1", None)

    def test_custom_timeout_is_passed_to_wait(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """A custom ``within '{timeout}' seconds`` value overrides the global wait timeout."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_storage_json(),
            stderr="",
        )
        mocker.patch("time.monotonic", side_effect=[0.0, 999.0])

        with pytest.raises(TimeoutError, match="after 90"):
            assert_storage_attached(context, 99, "ost", "lustre-server/1", None, timeout=90.0)


class TestWaitFor:
    """Test the ``wait_for`` checkpoint step handler."""

    @staticmethod
    @scenario(REUSABLE_THEN_STEP_TESTS, "Wait for a number of seconds")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``wait_for`` with only the required clause.

        Notes:
            - No assertion is needed. ``time.sleep`` is mocked as a no-op by the
              autouse ``_mock_time`` fixture. Reaching this point means the
              Gherkin step parsed and the handler ran without error.
        """

    def test_sleeps_for_requested_duration(self, mocker: MockerFixture) -> None:
        """``wait_for`` sleeps for the parsed number of seconds."""
        mock_sleep = mocker.patch("time.sleep")

        wait_for("10")

        mock_sleep.assert_called_once_with(10.0)

    def test_accepts_fractional_seconds(self, mocker: MockerFixture) -> None:
        """``wait_for`` accepts fractional durations."""
        mock_sleep = mocker.patch("time.sleep")

        wait_for("2.5")

        mock_sleep.assert_called_once_with(2.5)

    def test_raises_when_not_a_number(self) -> None:
        """``wait_for`` raises when the duration is not a number."""
        with pytest.raises(ValueError, match="'ten' is not a number"):
            wait_for("ten")

    def test_raises_when_negative(self) -> None:
        """``wait_for`` raises when the duration is negative."""
        with pytest.raises(ValueError, match="is negative"):
            wait_for("-1")
