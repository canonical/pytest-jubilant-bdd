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

"""``pytest-jubilant-bdd`` - a ``jubilant`` wrapper for writing behavior-driven tests with Gherkin.

The plugin provides reusable Gherkin step handlers, fixtures, markers, and options
for behavior-driven testing of Juju charmed operators.
"""

__all__ = ["Context", "assertions", "flexible", "make_dict", "make_list"]

from ._assertions import assertions
from ._context import Context
from ._parsers import flexible, make_dict, make_list
