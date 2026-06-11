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

"""Custom ``pytest-bdd`` parsers."""

__all__ = ["flexible"]

import re
from typing import Any

from pytest_bdd.parsers import StepParser

_OPTIONAL_REGEX = re.compile(r"\[(.+?)]")
"""Matches any string encapsulated in brackets.

Examples:
    >>> "[from channel 'latest/stable']"
    >>> "[on base 'ubuntu@24.04']"
"""


class flexible(StepParser):  # noqa N802
    """``pytest-bdd`` parser with optional, reorderable clauses encapsulated in brackets.

    Examples:
        >>> flexible("I deploy '{app}' [from channel '{channel}'] [with base '{base}']")
        ... # {app: str, channel: str | None, base: str | None}
    """

    def __init__(self, pattern: str) -> None:
        super().__init__(pattern)
        self._required_regex, self._optional_regexes = self._compile(pattern)

    def parse_arguments(self, name: str) -> dict[str, Any] | None:
        """Parse fields in Gherkin step.

        Args:
            name: Gherkin step content.

        Returns:
            A dictionary containing pytest fixture values.
        """
        required_match = self._required_regex.match(name)
        if not required_match:
            return None

        result = {k: v for k, v in required_match.groupdict().items() if v is not None}
        tail = name[required_match.end() :]
        for optional_regex in self._optional_regexes:
            optional_match = optional_regex.search(tail)
            if optional_match:
                result.update(
                    {
                        k: v
                        for k, v in optional_match.groupdict().items()
                        if v is not None
                    }
                )
                tail = tail[: optional_match.start()] + tail[optional_match.end() :]
            else:  # Set value of fixture(s) to `None` is there is no match.
                result.update({k: None for k in optional_regex.groupindex})

        # Pattern is not a match if there are remaining characters left over.
        if tail.strip():
            return None

        return result

    def is_matching(self, name: str) -> bool:
        """Determine if Gherkin step matches the configured pattern.

        Args:
            name: Gherkin step content.

        Returns:
            ``True`` if the Gherkin step matches the handler. ``False`` if otherwise.
        """
        return self.parse_arguments(name) is not None

    def _compile(self, pattern: str) -> tuple[re.Pattern[str], list[re.Pattern[str]]]:
        """Compile a Gherkin step into multiple regexes.

        Args:
            pattern: ``pytest-bdd`` step pattern to compile into regexes.
        """
        parts = _OPTIONAL_REGEX.split(pattern)

        required_text = parts[0].strip()  # Required text comes before optional clauses.
        required_regex = re.compile(self._build_regex(required_text))

        optional_text = [parts[i] for i in range(1, len(parts), 2)]
        optional_regexes = [
            re.compile(self._build_regex(optional)) for optional in optional_text
        ]

        return required_regex, optional_regexes

    def _build_regex(self, text: str) -> str:
        """Build a regular expression from a ``pytest-bdd`` step.

        Converts '{name}' placeholders to '(?P<name>[^']+)' regular expression groups.

        Args:
            `text`: Text containing ``pytest-bdd`` placeholders.
        """
        return re.sub(r"\\{(\w+)\\}", r"(?P<\1>[^']+)", re.escape(text))
