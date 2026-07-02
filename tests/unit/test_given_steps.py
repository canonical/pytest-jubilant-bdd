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

"""Unit tests for reusable *Given* Gherkin steps."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from constants import MODEL_SUFFIX, REUSABLE_GIVEN_STEP_TESTS
from helpers import make_app_without_relation, make_status_json
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_bdd import scenario

from pytest_jubilant_bdd import Context

# ruff: disable[SLF001]
from pytest_jubilant_bdd._main import (
    add_unit,
    deploy_local,
    is_deployed,
    is_integrated,
    model_exists,
    pack_charm,
    reset_app_config,
    reset_model_config,
    set_app_config,
    set_model_config,
)

# ruff: enable[SLF001]
from pytest_jubilant_bdd.errors import CharmNotFoundError, ModelNotFoundError


@pytest.fixture(scope="function")
def fake_charm_file(fs: FakeFilesystem) -> str:
    """Create a fake ``*.charm`` file on the pyfakefs filesystem.

    Returns the absolute path to the created file.
    """
    path = "/tmp/fake.charm"
    fs.create_file(path, contents="fake charm contents")
    return path


@pytest.fixture(scope="function")
def slurmctld_charm_path() -> str:
    """Env var name for the ``slurmctld`` charm path used by ``deploy_local``."""
    return "SLURMCTLD_CHARM_PATH"


@pytest.fixture(scope="function", autouse=True)
def _set_slurmctld_charm_env(
    monkeypatch: pytest.MonkeyPatch,
    slurmctld_charm_path: str,
    fake_charm_file: str,
) -> None:
    """Set ``SLURMCTLD_CHARM_PATH`` for all tests in this module.

    This ensures the ``deploy_local`` step handler can resolve the charm
    path from the environment variable when ``located at '{path}'`` is
    omitted from the Gherkin step.
    """
    monkeypatch.setenv(slurmctld_charm_path, fake_charm_file)


@pytest.fixture(scope="function")
def fake_packed_charm(fs: FakeFilesystem) -> None:
    """Create fake ``*.charm`` files for ``pack_charm`` tests.

    ``pack_charm`` uses ``Path.cwd()`` when no project directory is
    given, so the fake file must exist at the fake filesystem root. The
    optional-clause test uses ``/path/to/project`` as its project
    directory, so a second fake file is created there.
    """
    fs.create_file(
        "/my-charm_ubuntu-24.04-amd64.charm",
        contents="fake charm contents",
    )
    fs.create_file(
        "/path/to/project/my-charm_ubuntu-24.04-amd64.charm",
        contents="fake charm contents",
    )


class TestAddModel:
    """Test the ``add_model`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add model")
    def test_required(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``add_model`` with only the required clause."""
        model = f"test-{MODEL_SUFFIX}"

        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-model",
            "--no-switch",
            model,
        ]
        assert model in context.models


class TestAddUnit:
    """Test the ``add_unit`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add unit")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_unit`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-unit",
            "slurmctld",
            "--num-units",
            "3",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add unit in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_unit`` with the ``in model`` optional clause.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising the optional is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-unit",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "slurmctld",
            "--num-units",
            "2",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``add_unit`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            add_unit(context, 3, "slurmctld", "nonexistent")


class TestPackCharm:
    """Test the ``pack_charm`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Pack charm")
    def test_required(
        mock_subprocess_run: MagicMock,
        fake_packed_charm: None,
    ) -> None:
        """Test ``pack_charm`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "charmcraft",
            "-v",
            "pack",
        ]
        assert mock_subprocess_run.call_args[1]["cwd"] == Path("/")

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Pack charm from project directory")
    def test_with_optionals(
        mock_subprocess_run: MagicMock,
        fake_packed_charm: None,
    ) -> None:
        """Test ``pack_charm`` with all optional clauses."""
        assert mock_subprocess_run.call_args[0][0] == [
            "charmcraft",
            "-v",
            "pack",
        ]
        assert mock_subprocess_run.call_args[1]["cwd"] == Path("/path/to/project")

    def test_raises_when_charmcraft_missing(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``pack_charm`` raises when ``charmcraft`` is not on PATH."""
        mock_subprocess_run.side_effect = FileNotFoundError

        with pytest.raises(
            FileNotFoundError,
            match="'charmcraft' is not installed or not found on PATH",
        ):
            pack_charm(context, "my-charm", None)

    def test_raises_when_no_charm_file_found(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        fs: FakeFilesystem,
    ) -> None:
        """``pack_charm`` raises when no ``*.charm`` file is produced."""
        with pytest.raises(
            FileNotFoundError,
            match="No .charm file found for 'my-charm'",
        ):
            pack_charm(context, "my-charm", "/path/to/project")


class TestDeploy:
    """Test the ``deploy`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``deploy`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            "slurmctld",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy with all optionals")
    def test_with_optionals(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``deploy`` with all optional clauses.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising all optionals is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "slurmctld",
            "controller",
            "--base",
            "ubuntu@24.04",
            "--channel",
            "latest/edge",
            "--num-units",
            "3",
        ]
        assert f"test-{MODEL_SUFFIX}" in context.models


class TestDeployLocal:
    """Test the ``deploy_local`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises`` directly.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy local")
    def test_required(mock_subprocess_run: MagicMock, fake_charm_file: str) -> None:
        """Test ``deploy_local`` with only the required clause.

        When ``located at '{path}'`` is omitted, the handler resolves the
        charm path from the ``<APP>_CHARM_PATH`` environment variable, which
        is set by the ``_set_slurmctld_charm_env`` autouse fixture.

        When ``in model '{model}'`` is omitted, the handler uses the default
        Juju harness (not the one tracked in the testing context), so the
        ``--model`` flag is not included in the deploy command.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            fake_charm_file,
            "slurmctld",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy local with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock, fake_charm_file: str) -> None:
        """Test ``deploy_local`` with all optional clauses.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising all optionals is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            "--model",
            f"test-{MODEL_SUFFIX}",
            fake_charm_file,
            "controller",
            "--base",
            "ubuntu@24.04",
            "--num-units",
            "3",
        ]

    def test_raises_when_env_var_missing(
        self,
        context: Context,
        monkeypatch: pytest.MonkeyPatch,
        slurmctld_charm_path: str,
    ) -> None:
        """``deploy_local`` raises when ``<APP>_CHARM_PATH`` is not set."""
        monkeypatch.delenv(slurmctld_charm_path, raising=False)

        with pytest.raises(
            CharmNotFoundError,
            match=f"Charm not found: environment variable '{slurmctld_charm_path}' is not set.",
        ):
            deploy_local(context, "slurmctld", None, None, None, 1, None)

    def test_raises_when_path_missing(self, context: Context) -> None:
        """``deploy_local`` raises when the supplied path is not a file."""
        nonexistent = Path("/nonexistent/does-not-exist.charm")

        with pytest.raises(
            CharmNotFoundError,
            match=f"Charm not found: '{nonexistent}' is not a file",
        ):
            deploy_local(context, "slurmctld", nonexistent, None, None, 1, None)


class TestIntegrate:
    """Test the ``integrate`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Integrate")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``integrate`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "integrate",
            "slurmctld",
            "slurmd",
        ]


class TestModelExists:
    """Test the ``model_exists`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Model exists")
    def test_when_model_exists(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``model_exists`` when the model is present in the context."""
        assert f"test-{MODEL_SUFFIX}" in context.models

    def test_raises_when_missing(self, context: Context) -> None:
        """``model_exists`` raises an ``AssertionError`` when the model is absent."""
        with pytest.raises(AssertionError):
            model_exists(context, "definitely-not-a-real-model")


class TestIsIntegrated:
    """Test the ``is_integrated`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises`` in the body.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is integrated")
    def test_when_integrated(
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
    ) -> None:
        """Test ``is_integrated`` when the relation exists.

        No assertion is needed: the step handler raises ``AssertionError`` if
        the relation is missing. Reaching this point means the assertion passed.
        """

    def test_raises_when_not_integrated(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """Test ``is_integrated`` raises an ``AssertionError`` when the integration is absent."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json({"slurmctld": make_app_without_relation("slurmctld")}),
            stderr="",
        )

        with pytest.raises(
            AssertionError,
            match="'slurmctld' is not integrated with 'slurmd'",
        ):
            is_integrated(context, "slurmctld", "slurmd")


class TestIsDeployed:
    """Test the ``is_deployed`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises`` in the body.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is deployed")
    def test_required(
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
    ) -> None:
        """Test ``is_deployed`` with only the required clause.

        No assertion is needed: the step handler raises ``AssertionError`` if
        the app is not found. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is deployed in model")
    def test_with_optionals(
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
    ) -> None:
        """Test ``is_deployed`` with the ``in model '{model}'`` optional clause.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising the optional is sufficient.

        No assertion is needed: the step handler raises ``AssertionError`` if
        the app is not found. Reaching this point means the assertion passed.
        """

    def test_raises_when_not_found(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``is_deployed`` raises when the app is not found."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json(apps={}),
            stderr="",
        )

        with pytest.raises(AssertionError, match="'slurmctld' is not deployed"):
            is_deployed(context, "slurmctld", None)

    def test_raises_when_not_found_in_model(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``is_deployed`` raises with model context when the app is missing."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json(apps={}),
            stderr="",
        )

        with pytest.raises(
            AssertionError,
            match="'slurmctld' is not deployed in model 'test'",
        ):
            is_deployed(context, "slurmctld", "test")


class TestResetAppConfig:
    """Test the ``reset_app_config`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Reset app config")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``reset_app_config`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "config",
            "slurmctld",
            "--reset",
            "debug",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Reset app config in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``reset_app_config`` with the ``in model`` optional clause.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising the optional is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "config",
            "--model",
            f"test2-{MODEL_SUFFIX}",
            "slurmctld",
            "--reset",
            "debug",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``reset_app_config`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            reset_app_config(context, "debug", "slurmctld", "nonexistent")


class TestSetAppConfig:
    """Test the ``set_app_config`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Set app config")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``set_app_config`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "config",
            "slurmctld",
            "debug=true",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Set app config in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``set_app_config`` with the ``in model`` optional clause.

        Notes:
            The ``flexible`` parser allows optional clauses to appear in any
            order, so a single test exercising the optional is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "config",
            "--model",
            f"test2-{MODEL_SUFFIX}",
            "slurmctld",
            "debug=true",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``set_app_config`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            set_app_config(context, "debug", "slurmctld", "true", "nonexistent")


class TestSetModelConfig:
    """Test the ``set_model_config`` *Given* step handler.

    Notes:
        Error paths and the ``cloudinit-userdata`` file-reading path are
        tested by calling the handler directly rather than via ``@scenario``
        because ``@scenario`` runs the Gherkin steps before the test body, so
        exceptions raised during step execution cannot be caught with
        ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Set model config")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``set_model_config`` with the required clauses."""
        model_config_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call.args[0] and call.args[0][1] == "model-config"
        ]
        assert len(model_config_calls) == 1
        assert model_config_calls[0].args[0] == [
            "juju",
            "model-config",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "update-status-hook-interval=10s",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``set_model_config`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            set_model_config(context, "update-status-hook-interval", "nonexistent", "10s")

    def test_reads_cloudinit_userdata_file(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        fs: FakeFilesystem,
    ) -> None:
        """``set_model_config`` reads the file at ``value`` for ``cloudinit-userdata``."""
        cloudinit_path = "/tmp/cloudinit.yaml"
        cloudinit_content = "#cloud-config\npackages:\n  - curl\n"
        fs.create_file(cloudinit_path, contents=cloudinit_content)

        # Add the model directly to the testing context so the handler can
        # resolve a `Juju` harness without going through the `add_model`
        # Gherkin step.
        context.models.add("test")

        set_model_config(context, "cloudinit-userdata", "test", cloudinit_path)

        model_config_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call.args[0] and call.args[0][1] == "model-config"
        ]
        assert len(model_config_calls) == 1
        assert model_config_calls[0].args[0] == [
            "juju",
            "model-config",
            "--model",
            f"test-{MODEL_SUFFIX}",
            f"cloudinit-userdata={cloudinit_content}",
        ]

    def test_raises_when_cloudinit_userdata_file_missing(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``set_model_config`` raises ``FileNotFoundError`` when the cloud-init file is missing."""
        # Add the model directly to the testing context so the handler can
        # resolve a `Juju` harness. The file-read error must surface before
        # the subprocess call, so the model lookup is irrelevant.
        context.models.add("test")

        with pytest.raises(
            FileNotFoundError,
            match="Cloud-init user data file not found: '/tmp/missing-cloudinit.yaml'",
        ):
            set_model_config(context, "cloudinit-userdata", "test", "/tmp/missing-cloudinit.yaml")


class TestResetModelConfig:
    """Test the ``reset_model_config`` *Given* step handler.

    Notes:
        Error paths are tested by calling the handler directly rather
        than with ``@scenario`` because ``@scenario`` runs the Gherkin steps
        before the test body, so exceptions raised during step execution
        cannot be caught with ``pytest.raises``.
    """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Reset model config")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``reset_model_config`` with the required clauses."""
        model_config_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call.args[0] and call.args[0][1] == "model-config"
        ]
        assert len(model_config_calls) == 1
        assert model_config_calls[0].args[0] == [
            "juju",
            "model-config",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "--reset",
            "update-status-hook-interval",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``reset_model_config`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            reset_model_config(context, "update-status-hook-interval", "nonexistent")
