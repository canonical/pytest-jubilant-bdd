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

"""Track and control testing contexts."""

import secrets
from collections import deque
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field

from jubilant import Juju, Task
from jubilant.statustypes import AppStatus, UnitStatus

from ._errors import (
    AppNotFoundError,
    ModelNotFoundError,
    TooManyDeployedAppsError,
    UnitNotFoundError,
)


class stack[T]:  # noqa N802
    """Strict Stack data structure API for tracking completed Juju tasks."""

    def __init__(self, iterable: Iterable[T] = ()) -> None:
        self._data = deque(iterable)

    def push(self, v: T, /) -> None:
        """Push value into the stack.

        Args:
            v: Value to push into the stack.
        """
        self._data.append(v)

    def pop(self) -> T:
        """Pop a value from the stack.

        Raises:
            IndexError: Raised if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Pop from an empty stack")

        return self._data.pop()

    def peek(self) -> T:
        """Peek at the current top value in the stack.

        Raises:
            IndexError: Raised if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Peek from an empty stack")

        return self._data[-1]

    def is_empty(self) -> bool:
        """Check if the stack is empty."""
        return len(self._data) == 0

    def __len__(self) -> int:  # noqa D105
        return len(self._data)


class ModelMapping(Mapping[str, Juju]):
    """Track models in a testing context.

    Args:
        postfix:
            Common slug shared by all models in a testing context.
            This value is used to ensure that there are no conflicts between models in the
            testing context and models that already exist in the current cloud/controller.
    """

    def __init__(self, *, postfix: str | None = None):
        self._data: dict[str, Juju] = {}
        self._postfix = postfix if postfix else secrets.token_hex(4)

    def add(self, model: str) -> None:
        """Add a new model to testing context.

        Args:
            model: Name of the new model.
        """
        juju = Juju()
        name = f"{model}-{self._postfix}"

        juju.add_model(name)

        self._data[name] = juju

    def __getitem__(self, model: str, /) -> Juju:  # noqa D105
        try:
            return self._data[f"{model}-{self._postfix}"]
        except KeyError:
            raise ModelNotFoundError(
                f"Model '{model}' not found. "
                f"Available models: {', '.join(model_ for model_ in self._data)}"
            )

    def __len__(self) -> int:  # noqa D105
        return len(self._data)

    def __iter__(self) -> Iterator[str]:  # noqa D105
        return iter(self._data)


@dataclass
class Context:
    """Object to track and control a testing context.

    Attributes:
        juju: Harness for interfacing with the Juju CLI.
        action_results: Stack that tracks the results of ``juju run``.
        exec_results: Stack that tracks the results of ``juju exec``.
        models: Mapping that tracks models in the testing context.
    """

    juju: Juju = Juju()
    action_results: stack[Task] = field(default_factory=stack)
    exec_results: stack[Task] = field(default_factory=stack)
    models: ModelMapping = field(default_factory=ModelMapping)

    def get_app(self, app: str, /, *, model: str | None = None) -> AppStatus:
        """Get an application.

        Args:
            app: Name of the application.
            model: Name of the model the application is deployed to.

        Raises:
            AppNotFoundError:
                Raised if the requested application is not found in any model.
            TooManyDeployedAppsError:
                Raised if multiple applications share the same name in the current
                testing context and no ``model`` was provided.
        """
        if model is not None:
            apps = self.models[model].status().apps
            try:
                return apps[app]
            except KeyError:
                raise AppNotFoundError(
                    f"App not found: '{app}' is not deployed in model '{model}'. "
                    f"Available apps: {', '.join(f'{app_}' for app_ in apps)}"
                ) from None

        result = None
        seen: dict[str, str] = {}
        for model_name, model_ in self.models.items():
            status = model_.status()

            if isinstance(result, AppStatus):
                raise TooManyDeployedAppsError(
                    f"App '{app}' is already present in model '{seen[app]}'. "
                    f"Provide a `model` name to get the app from a specific model"
                ) from None

            if app in status.apps:
                result = status.apps[app]
                seen[app] = model_name

        if result is None:
            raise AppNotFoundError(
                f"App not found: '{app}' is not deployed in any models"
            ) from None

        return result

    def get_unit(self, unit: str, /, *, model: str | None = None) -> UnitStatus:
        """Get a unit.

        Args:
            unit: Name of the unit.
            model: Name of the model the unit is deployed in.

        Raises:
            AppNotFoundError:
                Raised if the requested application is not found in any model.
            TooManyDeployedAppsError:
                Raised if multiple applications share the same name in the current
                testing context and no ``model`` was provided.
            UnitNotFoundError:
                Raised if the requested unit is not found under its application namespace.
        """
        app_name = unit.split("/")[0]
        app = self.get_app(app_name, model=model)
        try:
            return app.units[unit]
        except KeyError:
            raise UnitNotFoundError(
                f"Unit not found: '{unit}' is not deployed in app '{app_name}'. "
                f"Available units: {', '.join(f'{unit_}' for unit_ in app.units)}"
            ) from None
