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

"""Custom error classes used in ``pytest-jubilant-bdd``."""


class AppNotFoundError(Exception):
    """Error raised if an application is not found."""


class CharmNotFoundError(FileNotFoundError):
    """Error raised if a ``*.charm`` file is not found on the system."""


class ModelNotFoundError(Exception):
    """Error raised if model is not found."""


class TooManyDeployedAppsError(Exception):
    """Error raised if a search returns more than one application."""


class UnitNotFoundError(Exception):
    """Error raised if a unit is not found."""


class WaitError(Exception):
    """Error when :meth:`Context.wait`'s ``error`` callable returns ``True``."""
