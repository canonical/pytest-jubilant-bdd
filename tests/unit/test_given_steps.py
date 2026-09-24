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

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from constants import MODEL_SUFFIX, REUSABLE_GIVEN_STEP_TESTS
from helpers import make_app_without_relation, make_status_json
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_bdd import scenario

from pytest_jubilant_bdd import Context

# ruff: disable[SLF001]
from pytest_jubilant_bdd._main import (
    add_machine,
    add_storage,
    add_unit,
    consume_offer,
    create_offer,
    deploy_local,
    disintegrate,
    integrate,
    is_app_config_set,
    is_deployed,
    is_integrated,
    model_exists,
    pack_charm,
    remove_storage,
    remove_unit,
    reset_app_config,
    reset_model_config,
    set_app_config,
    set_model_config,
    switch_model,
)

# ruff: enable[SLF001]
from pytest_jubilant_bdd.errors import ModelNotFoundError


@pytest.fixture(scope="function")
def fake_charm_file(fs: FakeFilesystem) -> str:
    """Create a fake ``*.charm`` file on the pyfakefs filesystem."""
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


@pytest.fixture(scope="function", autouse=True)
def _reset_context(context: Context) -> None:
    """Clear session-scoped state before each test.

    The ``context`` fixture is session-scoped, so the default model
    persists across tests. Clearing it ensures a clean slate.
    """
    context.default_model = None


@pytest.fixture(scope="function")
def mock_config_json(mock_subprocess_run: MagicMock) -> None:
    """Configure ``mock_subprocess_run`` to return a valid config JSON.

    ``is_app_config_set`` calls ``juju.config()`` (which runs
    ``juju config --format json``), so the mock must return a config
    payload for that command.
    """
    mock_subprocess_run.side_effect = _config_side_effect()


def _config_side_effect(
    config_value: bool = True,
) -> Callable[..., MagicMock]:
    """Build a ``subprocess.run`` side effect returning config JSON.

    Args:
        config_value: Value of the ``debug`` option in the ``juju config`` payload.
    """

    def _side_effect(*args: object, **kwargs: object) -> MagicMock:
        cmd = cast(list[str], args[0])
        if cmd[0:2] == ["juju", "config"]:
            return MagicMock(
                stdout=json.dumps(
                    {"settings": {"debug": {"type": "bool", "value": config_value}}}
                ),
                stderr="",
            )
        return MagicMock(stdout="", stderr="")

    return _side_effect


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
    """Test the ``add_unit`` *Given* step handler."""

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
        """Test ``add_unit`` with the ``in model`` optional clause."""
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


class TestAddMachine:
    """Test the ``add_machine`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add machine")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_machine`` with the singular ``a`` article form."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-machine",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add machine with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_machine`` with the counted form and all optional clauses."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-machine",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "lxd:25",
            "--base",
            "ubuntu@24.04",
            "--constraints",
            "mem=8G",
            "--constraints",
            "cores=4",
            "--disks",
            "ebs,1T,2",
            "-n",
            "2",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``add_machine`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            add_machine(context, model="nonexistent")


class TestAddStorage:
    """Test the ``add_storage`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add storage")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_storage`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-storage",
            "lustre-server/1",
            "ost=1",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Add storage with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``add_storage`` with all optional clauses.

        Notes:
            - The ``flexible`` parser matches optional clauses in any order,
              so a single "all optionals" scenario is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "add-storage",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "lustre-server/1",
            "ost=loop,3,1G",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``add_storage`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            add_storage(context, "ost", "lustre-server/1", None, None, 1, "nonexistent")


class TestRemoveUnit:
    """Test the ``remove_unit`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Remove unit")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``remove_unit`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-unit",
            "--no-prompt",
            "slurmctld/0",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Remove unit in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``remove_unit`` with all optional clauses."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-unit",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "--no-prompt",
            "slurmctld/0",
            "slurmctld/1",
            "slurmctld/2",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``remove_unit`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            remove_unit(context, ["slurmctld/0"], "nonexistent")


class TestRemoveStorage:
    """Test the ``remove_storage`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Remove storage")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``remove_storage`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-storage",
            "ost/0",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Remove storage in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``remove_storage`` with all optional clauses.

        Notes:
            - The ``flexible`` parser matches list elements with any
              conjunction style, so one multi-instance scenario is sufficient.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-storage",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "ost/0",
            "ost/1",
            "ost/2",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``remove_storage`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            remove_storage(context, ["ost/0"], "nonexistent")


class TestPackCharm:
    """Test the ``pack_charm`` *Given* step handler."""

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

    def test_skips_when_env_var_is_set(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``pack_charm`` skips ``charmcraft pack`` when ``<APP>_CHARM_PATH`` is set."""
        charm_path = "/tmp/prebuilt/slurmctld.charm"
        monkeypatch.setenv("SLURMCTLD_CHARM_PATH", charm_path)

        pack_charm(context, "slurmctld", None)

        mock_subprocess_run.assert_not_called()


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
        """Test ``deploy`` with all optional clauses."""
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
            "--constraints",
            "virt-type=virtual-machine",
            "--constraints",
            "cores=4",
            "--constraints",
            "mem=5G",
            "--num-units",
            "3",
        ]
        assert f"test-{MODEL_SUFFIX}" in context.models


class TestDeployLocal:
    """Test the ``deploy_local`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy local")
    def test_required(mock_subprocess_run: MagicMock, fake_charm_file: str) -> None:
        """Test ``deploy_local`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            fake_charm_file,
            "slurmctld",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Deploy local with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock, fake_charm_file: str) -> None:
        """Test ``deploy_local`` with all optional clauses."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "deploy",
            "--model",
            f"test-{MODEL_SUFFIX}",
            fake_charm_file,
            "controller",
            "--base",
            "ubuntu@24.04",
            "--constraints",
            "virt-type=virtual-machine",
            "--constraints",
            "cores=4",
            "--constraints",
            "mem=5G",
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
            FileNotFoundError,
            match=f"Charm not found: environment variable '{slurmctld_charm_path}' is not set.",
        ):
            deploy_local(context, "slurmctld", None, None, None, 1, None, {})

    def test_raises_when_path_missing(self, context: Context) -> None:
        """``deploy_local`` raises when the supplied path is not a file."""
        nonexistent = Path("/nonexistent/does-not-exist.charm")

        with pytest.raises(
            FileNotFoundError,
            match=f"Charm not found: '{nonexistent}' is not a file",
        ):
            deploy_local(context, "slurmctld", nonexistent, None, None, 1, None, {})


class TestCreateOffer:
    """Test the ``create_offer`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Create offer")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``create_offer`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "offer",
            "mysql:db",
            "mysql-offer",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Create offer with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``create_offer`` with all optional clauses present.

        Notes:
            ``juju offer`` does not accept a ``--model`` flag; jubilant
            embeds the model in a dotted ``<model>.<app>:<endpoint>``
            argument instead.
        """
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "offer",
            f"test-{MODEL_SUFFIX}.mysql:db",
            "mysql-offer",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``create_offer`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            create_offer(context, "mysql-offer", "mysql", "db", "nonexistent")


class TestConsumeOffer:
    """Test the ``consume_offer`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Consume offer")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``consume_offer`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "consume",
            "othermodel.mysql",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Consume offer with all optionals")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``consume_offer`` with all optional clauses present."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "consume",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "othermodel.mysql",
            "sql",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``consume_offer`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            consume_offer(context, "othermodel.mysql", None, "nonexistent")


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

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Integrate in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``integrate`` with the ``in model`` optional clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "integrate",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "slurmctld",
            "slurmd",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``integrate`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            integrate(context, "slurmctld", "slurmd", "nonexistent")


class TestDisintegrate:
    """Test the ``disintegrate`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Disintegrate")
    def test_required(mock_subprocess_run: MagicMock) -> None:
        """Test ``disintegrate`` with only the required clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-relation",
            "slurmctld",
            "slurmd",
        ]

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Disintegrate in model")
    def test_with_optionals(mock_subprocess_run: MagicMock) -> None:
        """Test ``disintegrate`` with the ``in model`` optional clause."""
        assert mock_subprocess_run.call_args[0][0] == [
            "juju",
            "remove-relation",
            "--model",
            f"test-{MODEL_SUFFIX}",
            "slurmctld",
            "slurmd",
        ]

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``disintegrate`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            disintegrate(context, "slurmctld", "slurmd", "nonexistent")


class TestModelExists:
    """Test the ``model_exists`` *Given* step handler."""

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
    """Test the ``is_integrated`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is integrated")
    def test_when_integrated(
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
    ) -> None:
        """Test ``is_integrated`` when the relation exists.

        Notes:
            - No assertion is needed. The step handler raises ``AssertionError`` if
              the integration is missing. Reaching this point means the assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is integrated in model")
    def test_with_optionals(mock_subprocess_run: MagicMock, mock_status_json: None) -> None:
        """Test ``is_integrated`` with the ``in model`` optional clause.

        Notes:
            - No assertion is needed. The step handler raises ``AssertionError`` if
              the integration is missing. Reaching this point means the assertion passed.
        """

    def test_raises_when_not_integrated(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``is_integrated`` raises an ``AssertionError`` when the integration is absent."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json({"slurmctld": make_app_without_relation("slurmctld")}),
            stderr="",
        )

        with pytest.raises(
            AssertionError,
            match="'slurmctld' is not integrated with 'slurmd'",
        ):
            is_integrated(context, "slurmctld", "slurmd", None)

    def test_raises_when_not_found(self, context: Context, mock_subprocess_run: MagicMock) -> None:
        """``is_integrated`` raises when ``app_one`` is not deployed."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json(apps={}),
            stderr="",
        )

        with pytest.raises(AssertionError, match="'slurmctld' is not deployed"):
            is_integrated(context, "slurmctld", "slurmd", None)

    def test_raises_when_not_integrated_in_model(
        self,
        context: Context,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """``is_integrated`` raises with model context when the integration is absent."""
        mock_subprocess_run.return_value = MagicMock(
            stdout=make_status_json({"slurmctld": make_app_without_relation("slurmctld")}),
            stderr="",
        )

        with pytest.raises(
            AssertionError,
            match="'slurmctld' is not integrated with 'slurmd' in model 'test'",
        ):
            is_integrated(context, "slurmctld", "slurmd", "test")


class TestIsDeployed:
    """Test the ``is_deployed`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Is deployed")
    def test_required(
        context: Context,
        mock_subprocess_run: MagicMock,
        mock_status_json: None,
    ) -> None:
        """Test ``is_deployed`` with only the required clause.

        Notes:
            - No assertion is needed: the step handler raises ``AssertionError`` if
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
            - No assertion is needed. The step handler raises ``AssertionError`` if
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


class TestIsAppConfigSet:
    """Test the ``is_app_config_set`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "App config is set")
    def test_required(mock_subprocess_run: MagicMock, mock_config_json: None) -> None:
        """Test ``is_app_config_set`` with only the required clause.

        Notes:
            - No assertion is needed. The step handler raises ``AssertionError`` if
              the config value does not match. Reaching this point means the
              assertion passed.
        """

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "App config is set in model")
    def test_with_optionals(mock_subprocess_run: MagicMock, mock_config_json: None) -> None:
        """Test ``is_app_config_set`` with the ``in model`` optional clause.

        Notes:
            - No assertion is needed. The step handler raises ``AssertionError`` if
              the config value does not match. Reaching this point means the
              assertion passed.
        """

    def test_raises_when_not_set(self, context: Context, mock_subprocess_run: MagicMock) -> None:
        """``is_app_config_set`` raises when the config value does not match."""
        mock_subprocess_run.side_effect = _config_side_effect(config_value=False)
        with pytest.raises(
            AssertionError,
            match="Option 'debug' for app 'slurmctld' is not set to 'true'",
        ):
            is_app_config_set(context, "debug", "slurmctld", "true", None)


class TestResetAppConfig:
    """Test the ``reset_app_config`` *Given* step handler."""

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
        """Test ``reset_app_config`` with the ``in model`` optional clause."""
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
    """Test the ``set_app_config`` *Given* step handler."""

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
        """Test ``set_app_config`` with the ``in model`` optional clause."""
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
    """Test the ``set_model_config`` *Given* step handler."""

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
    """Test the ``reset_model_config`` *Given* step handler."""

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


class TestSwitchModel:
    """Test the ``switch_model`` *Given* step handler."""

    @staticmethod
    @scenario(REUSABLE_GIVEN_STEP_TESTS, "Switch model")
    def test_required(context: Context, mock_subprocess_run: MagicMock) -> None:
        """Test ``switch_model`` with the required clause."""
        assert context.default_model == f"test-{MODEL_SUFFIX}"

    def test_raises_when_model_missing(self, context: Context) -> None:
        """``switch_model`` raises when the model is not in the context."""
        with pytest.raises(ModelNotFoundError, match="Model 'nonexistent' not found"):
            switch_model(context, "nonexistent")
