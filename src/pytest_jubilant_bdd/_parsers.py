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

__all__ = ["flexible", "make_dict", "make_list"]

import ast
import re
from typing import Any

from pytest_bdd.parsers import StepParser


_FIND_OPTIONAL_REGEX = re.compile(r"%.*?%|\[((?:[^]%]|%.*?%)+?)]")
r"""Regular expression that matches any clause encapsulated in square brackets (``[`` and ``]``).

Does not match any bracket characters wrapped surrounded with percent signs (``%``).

Notes:
    This pattern uses a "Match and Skip" strategy to extract text inside square brackets 
    [like this] while safely ignoring any closing brackets "]" that are trapped inside percent 
    blocks %...%.
    
    Breakdown:

    %.*?%               -> SKIP SIDE: Matches and consumes an entire %block% so the engine 
                           skips looking for brackets inside it. No capture group here.
    |                   -> OR
    \[                  -> MATCH SIDE: Matches a literal opening square bracket.
    (                   -> START CAPTURE GROUP 1: The text we actually want to extract.
      (?:               -> Non-capturing group to evaluate inner contents step-by-step:
        [^\]%]          -> Option A: Match any character that is NOT a closing bracket "]" or "%".
        |               -> OR
        %.*?%           -> Option B: Consume an entire nested %block% as a single unit, 
                           preventing internal patterns from triggering a premature cut-off.
      )+?               -> Repeat these options lazily, matching as little as possible...
    )                   -> END CAPTURE GROUP 1.
    \]                  -> ...until hitting the true literal closing square bracket.

Examples:
    >>> "[from channel 'latest/stable']"
    >>> "[on base 'ubuntu@24.04']"
    >>> "%(?P<units>'[^']+')%"  # Does not match.
"""

_REPLACE_BRACES_REGEX = re.compile(r"%.*?%|\{(\w+)}")
"""Regular expression that replaces braces (``{`` and ``}``) in a Gherkin step template.

Used to substitute text in Gherkin step with a named capture group.
"""

_STRIP_OPTIONAL_REGEX = re.compile(r"%.*?%|(\s*\[((?:[^]%]|%.*?%)+?)])")
"""Regular expression that matches optional clauses from a Gherkin step template for extraction.

Functionally similar to ``_FIND_OPTIONAL_REGEX``, but includes 
square brackets and optional whitespace in capture group 1.
"""

_STRIP_PERCENT_SIGN_REGEX = re.compile(r"%(.*?)%")
"""Regular express that matches the content in between two percent signs.

Used to strip percent signs before assembling the final regex for matching Gherkin steps. 
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
            pattern: ``pytest-bdd`` step pattern to compile into regular expressions.
        """
        optional_text = [
            match for match in _FIND_OPTIONAL_REGEX.findall(pattern) if match
        ]
        optional_regexes = [
            re.compile(self._build_regex(optional)) for optional in optional_text
        ]

        # The lambda checks if group 1 matched ([] block), then replace with nothing "".
        # If group 1 didn't match, that means group 0 (% block) matched, so return it untouched.
        required_text = _STRIP_OPTIONAL_REGEX.sub(
            lambda match: "" if match.group(1) else match.group(0), pattern
        )
        required_regex = re.compile(self._build_regex(required_text))

        return required_regex, optional_regexes

    def _build_regex(self, text: str) -> str:
        """Build a regular expression from a ``pytest-bdd`` step.

        Converts '{name}' placeholders to '(?P<name>[^']+)' regular expression groups.

        Args:
            `text`: Text containing ``pytest-bdd`` placeholders.
        """
        # Match content between two % signs, and keep only the content (\1)
        return _STRIP_PERCENT_SIGN_REGEX.sub(
            r"\1",
            # Replace braces not encapsulated by two % signs with named capture group.
            _REPLACE_BRACES_REGEX.sub(
                lambda match: (
                    f"(?P<{name}>[^']+)" if (name := match.group(1)) else match.group(0)
                ),
                text,
            ),
        )


def autocast(value: str) -> Any:
    """Autocast value to the 'best-fitting' Python type.

    Args:
        value: Value to cast to the best-fitting Python type.
    """
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def make_dict(value: str | None) -> dict[str, Any]:
    """Make a Python dictionary ``{'k': 'v'}`` from string ``k=v``."""
    if value is None:
        return {}

    matches = re.findall(r'(\w+)=("[^"]*"|\S+)', value)
    return {k: autocast(v.strip('"')) for k, v in matches}


def make_list(value: str | None) -> list[Any]:
    """Make a Python list ``['n1', 'n2', 'n3']`` from a serial list ``n1, n2, and n3``."""
    if value is None:
        return []

    matches = re.findall(r"'([^']+)'", value)
    return [autocast(match) for match in matches]
