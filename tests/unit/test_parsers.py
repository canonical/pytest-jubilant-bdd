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

"""Unit tests for the ``flexible`` parser."""

import pytest

from pytest_jubilant_bdd import flexible


class TestFlexible:
    """Test the ``flexible`` parser."""

    @pytest.fixture(scope="class")
    @classmethod
    def parser(cls) -> flexible:
        """Flexible Gherkin step parsing function."""
        return flexible(
            "I add machines [on base '{base}'] [with constraints '{constraints}'] [in model '{model}']"
        )

    def test_matches_whitespace_joined_optional_clauses(self, parser) -> None:
        """Optional clauses joined only by whitespace still match."""
        result = parser.parse_arguments(
            "I add machines on base 'ubuntu@24.04' with constraints 'mem=8G'"
        )

        assert result == {"base": "ubuntu@24.04", "constraints": "mem=8G", "model": None}

    def test_matches_and_joined_optional_clauses(self, parser) -> None:
        """Optional clauses joined with ``and`` are matched and parsed."""
        result = parser.parse_arguments(
            "I add machines on base 'ubuntu@24.04' and with constraints 'mem=8G'"
        )

        assert result == {"base": "ubuntu@24.04", "constraints": "mem=8G", "model": None}

    def test_matches_comma_joined_optional_clauses(self, parser) -> None:
        """Optional clauses joined with a bare comma are matched and parsed."""
        result = parser.parse_arguments(
            "I add machines on base 'ubuntu@24.04', with constraints 'mem=8G'"
        )

        assert result == {"base": "ubuntu@24.04", "constraints": "mem=8G", "model": None}

    def test_matches_oxford_comma_joined_optional_clauses(self, parser) -> None:
        """Optional clauses joined with ``, and`` are matched and parsed."""
        result = parser.parse_arguments(
            "I add machines on base 'ubuntu@24.04', and with constraints 'mem=8G'"
        )

        assert result == {"base": "ubuntu@24.04", "constraints": "mem=8G", "model": None}

    def test_matches_and_between_required_and_first_optional_clause(self, parser) -> None:
        """An ``and`` between the required text and the first optional clause matches."""
        result = parser.parse_arguments("I add machines and on base 'ubuntu@24.04'")

        assert result == {"base": "ubuntu@24.04", "constraints": None, "model": None}

    def test_matches_reordered_optional_clauses_joined_by_and(self, parser) -> None:
        """Optional clauses joined with ``and`` are matched in any order."""
        result = parser.parse_arguments(
            "I add machines in model 'test' and with constraints 'mem=8G' on base 'ubuntu@24.04'"
        )

        assert result == {"base": "ubuntu@24.04", "constraints": "mem=8G", "model": "test"}

    def test_matches_and_joined_percent_block_optional_clause(self) -> None:
        """An optional clause starting with a ``%...%`` block supports ``and`` joins."""
        parser = flexible(
            r"all agents are %'(?P<status>[^']+)'% [in %models? '(?P<models>[^']+)'%]"
        )

        result = parser.parse_arguments("all agents are 'idle' and in models 'test'")

        assert result == {"status": "idle", "models": "test"}

    def test_returns_none_when_conjunction_is_dangling(self, parser) -> None:
        """A trailing ``and`` with no following clause is not matched."""
        result = parser.parse_arguments("I add machines on base 'ubuntu@24.04' and")

        assert result is None

    def test_returns_none_when_conjunction_is_doubled(self, parser) -> None:
        """A doubled ``and`` between clauses is not matched."""
        result = parser.parse_arguments(
            "I add machines on base 'ubuntu@24.04' and and with constraints 'mem=8G'"
        )

        assert result is None

    def test_returns_none_when_comma_is_trailing(self, parser) -> None:
        """A trailing comma with no following clause is not matched."""
        result = parser.parse_arguments("I add machines on base 'ubuntu@24.04',")

        assert result is None
