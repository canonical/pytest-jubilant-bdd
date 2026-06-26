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

"""Constants used in the ``pytest-jubilant-bdd`` unit tests."""

from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
FEATURE_DIR = ROOT_DIR / "features"

# Type annotation for `pytest_bdd.scenario` accepts `str` and not `Path`.
REUSABLE_GIVEN_STEP_TESTS = str(FEATURE_DIR / "given.feature")
REUSABLE_THEN_STEP_TESTS = str(FEATURE_DIR / "then.feature")
REUSABLE_WHEN_STEP_TESTS = str(FEATURE_DIR / "when.feature")

MODEL_SUFFIX = "xyz123"
