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

"""Unit tests for the ``Context`` testing context."""

import pytest
from pytest_mock import MockerFixture

from pytest_jubilant_bdd import Context


class TestHostInfo:
    """Test the ``Context.host_info`` attribute."""

    @staticmethod
    def _context_with_machine(mocker: MockerFixture, machine: str) -> Context:
        """Create a ``Context`` with ``platform.machine`` patched.

        Args:
            mocker: The pytest-mock mocker fixture.
            machine: Value returned by the patched ``platform.machine``.

        Returns:
            A freshly constructed ``Context``.
        """
        mocker.patch("pytest_jubilant_bdd._context.platform.machine", return_value=machine)
        return Context()

    def test_arch_is_mapped_on_x86_64(self, mocker: MockerFixture) -> None:
        """``host_info['arch']`` maps ``x86_64`` to the Juju name ``amd64``."""
        context = self._context_with_machine(mocker, "x86_64")

        assert context.host_info["arch"] == "amd64"

    def test_arch_is_mapped_on_aarch64(self, mocker: MockerFixture) -> None:
        """``host_info['arch']`` maps ``aarch64`` to the Juju name ``arm64``."""
        context = self._context_with_machine(mocker, "aarch64")

        assert context.host_info["arch"] == "arm64"

    def test_arch_passthrough_unknown_machine(self, mocker: MockerFixture) -> None:
        """``host_info['arch']`` passes unknown machine values through normalized."""
        context = self._context_with_machine(mocker, "RISCV64")

        # Unknown values are lowercased and underscore-normalized but not mapped.
        assert context.host_info["arch"] == "riscv64"

    def test_host_info_is_read_only(self) -> None:
        """``host_info`` is a read-only mapping that rejects item assignment."""
        context = Context()

        with pytest.raises(TypeError):
            context.host_info["arch"] = "amd64"  # type: ignore[index]
