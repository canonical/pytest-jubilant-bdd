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

"""Unit tests for reusable *When* Gherkin steps."""

from unittest.mock import MagicMock

import pytest
from constants import MODEL_SUFFIX, REUSABLE_WHEN_STEP_TESTS
from helpers import make_task_json
from jubilant import Task
from pytest_bdd import scenario

from pytest_jubilant_bdd import Context


@pytest.fixture(scope="function", autouse=True)
def _reset_stacks(context: Context) -> None:
    """Clear ``action_results`` and ``exec_results`` stacks before each test.

    The ``context`` fixture is session-scoped, so stacks accumulate across
    tests. Clearing them ensures each test starts with a clean slate.
    """
    while not context.action_results.is_empty():
        context.action_results.pop()
    while not context.exec_results.is_empty():
        context.exec_results.pop()


@pytest.fixture(scope="function", autouse=True)
def _mock_task_json(mock_subprocess_run: MagicMock) -> None:
    """Configure ``mock_subprocess_run`` to return valid ``Task`` JSON.

    The ``juju run`` and ``juju exec`` commands return JSON containing a
    single ``Task`` object keyed by the unit or machine name. This fixture
    provides a default response that jubilant can parse into a ``Task``.
    """
    mock_subprocess_run.return_value = MagicMock(
        stdout=make_task_json("slurmctld/0"),
        stderr="",
    )


class TestRunAction:
    """Test the ``run_action`` *When* step handler."""

    @staticmethod
    @scenario(REUSABLE_WHEN_STEP_TESTS, "Run action on one unit")
    def test_required(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``run_action`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "run",
            "--format",
            "json",
            "slurmctld/0",
            "get-password",
        ]

        assert len(context.action_results) == 1
        task = context.action_results.peek()
        assert isinstance(task, Task)
        assert task.status == "completed"
        assert task.return_code == 0

    @staticmethod
    @scenario(REUSABLE_WHEN_STEP_TESTS, "Run action on multiple units with params in model")
    def test_with_optionals(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``run_action`` with all optional clauses.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising all optionals is sufficient.
        """
        run_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call.args[0] and call.args[0][0:2] == ["juju", "run"]
        ]
        assert len(run_calls) == 3

        units_called = [call.args[0][6] for call in run_calls]
        assert units_called == ["slurmctld/0", "slurmctld/1", "slurmctld/2"]

        for call in run_calls:
            assert "--model" in call.args[0]
            assert f"test-{MODEL_SUFFIX}" in call.args[0]
            assert "--params" in call.args[0]

        assert len(context.action_results) == 3


class TestRunExec:
    """Test the ``run_exec`` *When* step handler."""

    @staticmethod
    @scenario(REUSABLE_WHEN_STEP_TESTS, "Exec command on one machine")
    def test_run_exec_one_machine(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``run_exec`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "exec",
            "--format",
            "json",
            "--machine",
            "0",
            "--",
            "hostname",
        ]

        assert len(context.exec_results) == 1
        task = context.exec_results.peek()
        assert isinstance(task, Task)
        assert task.status == "completed"
        assert task.return_code == 0

    @staticmethod
    @scenario(REUSABLE_WHEN_STEP_TESTS, "Exec command on multiple units in model")
    def test_with_optionals(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``run_exec`` with all optional clauses.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising all optionals is sufficient.
        """
        exec_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call.args[0] and call.args[0][0:2] == ["juju", "exec"]
        ]
        assert len(exec_calls) == 3

        units_called = [call.args[0][7] for call in exec_calls]
        assert units_called == ["slurmd/0", "slurmd/1", "slurmd/2"]

        for call in exec_calls:
            assert "--model" in call.args[0]
            assert f"test-{MODEL_SUFFIX}" in call.args[0]
            assert "--unit" in call.args[0]

        assert len(context.exec_results) == 3
