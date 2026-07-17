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

"""Unit tests for the :class:`Context` object's per-scenario state.

These tests cover :attr:`Context.scenario_state` and the autouse
``_reset_scenario_state`` fixture registered in the plugin (``_main.py``).
They are not Gherkin step-handler tests, so they do not use the ``@scenario``
pattern described in the unit-testing skill.
"""

import pytest

from pytest_jubilant_bdd import Context


class TestScenarioState:
    """Test :attr:`Context.scenario_state` and its per-scenario reset."""

    def test_starts_empty(self, context: Context) -> None:
        """``scenario_state`` is an empty dict on a fresh ``Context``."""
        assert context.scenario_state == {}

    def test_starts_empty_on_fresh_instance(self) -> None:
        """A directly constructed ``Context`` has an empty ``scenario_state``.

        Notes:
            Verified without the session-scoped ``context`` fixture to confirm
            the default factory itself produces an empty mapping.
        """
        assert Context().scenario_state == {}

    def test_set_and_get(self, context: Context) -> None:
        """Values written under a semantic key are retrievable."""
        context.scenario_state["initial_token"] = "abc123"

        assert context.scenario_state["initial_token"] == "abc123"

    def test_supports_nested_values(self, context: Context) -> None:
        """``setdefault``-style nested writes work like a plain dict.

        Notes:
            Mirrors the slurm-charms pattern
            ``scenario_state.setdefault("jwt_keys", {})[unit] = key``.
        """
        context.scenario_state.setdefault("jwt_keys", {})["slurmctld/0"] = "key"

        assert context.scenario_state["jwt_keys"] == {"slurmctld/0": "key"}

    def test_supports_arbitrary_value_types(self, context: Context) -> None:
        """``scenario_state`` holds lists, dicts, and parsed JSON like a dict."""
        context.scenario_state["ha_controllers"] = {"primary": {"hostname": "node-0"}}
        context.scenario_state["diag_urls"] = ["http://a", "http://b"]
        context.scenario_state["initial_auth_key"] = {"keys": [{"k": "v"}]}

        assert context.scenario_state["ha_controllers"]["primary"]["hostname"] == "node-0"
        assert context.scenario_state["diag_urls"] == ["http://a", "http://b"]
        assert context.scenario_state["initial_auth_key"]["keys"][0]["k"] == "v"

    def test_clear_scenario_state(self, context: Context) -> None:
        """``clear_scenario_state`` removes all keys."""
        context.scenario_state["a"] = 1
        context.scenario_state["b"] = 2

        context.clear_scenario_state()

        assert context.scenario_state == {}

    def test_clear_scenario_state_is_idempotent(self, context: Context) -> None:
        """Calling ``clear_scenario_state`` on an already-empty state is a no-op."""
        context.clear_scenario_state()
        context.clear_scenario_state()

        assert context.scenario_state == {}

    def test_autouse_fixture_clears_state_via_method(self, context: Context) -> None:
        """The ``_reset_scenario_state`` fixture clears state.

        Notes:
            The ``_reset_scenario_state`` fixture (in the plugin, ``_main.py``) is autouse
            and function-scoped, so it has already run before this test body
            (state is empty at the start — see ``test_starts_empty``).
            Function-scoped fixtures are cached per test, so
            ``request.getfixturevalue`` cannot re-invoke it. Instead, this test
            verifies the contract directly: writing a sentinel and calling
            ``clear_scenario_state`` (the exact method the autouse fixture
            calls) clears the mapping. Combined with ``test_starts_empty``
            running before every test, this confirms the per-scenario reset
            behavior.
        """
        assert context.scenario_state == {}  # Autouse fixture already ran.
        context.scenario_state["sentinel"] = "from-this-test"

        context.clear_scenario_state()

        assert context.scenario_state == {}


@pytest.fixture(scope="function", autouse=True)
def _reset_default_model(context: Context) -> None:
    """Clear the session-scoped default model before each test.

    The ``context`` fixture is session-scoped, so ``default_model`` persists
    across tests. Clearing it ensures a clean slate. ``scenario_state`` is
    cleared by the autouse ``_reset_scenario_state`` fixture in the plugin.
    """
    context.default_model = None
