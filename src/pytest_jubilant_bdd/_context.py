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
        action_results: Stack that tracks the results of ``juju run``.
        exec_results: Stack that tracks the results of ``juju exec``.
        models: Mapping that tracks models in the testing context.
    """

    action_results: stack[Task] = field(default_factory=stack)
    exec_results: stack[Task] = field(default_factory=stack)
    models: ModelMapping = field(default_factory=ModelMapping)

    def get_juju(self, model: str | None = None) -> Juju:
        """Get a Juju CLI harness.

        Args:
            model:
                Name of the model that the created harness will operate on.
                If ``None``, the harness will operate on the current model
                the CLI client is switched to.

        Raises:
            ModelNotFoundError:
                Raised if a model name is provided, but the model does not
                exist in the current testing context.
        """
        if model:
            return self.models[model]

        return Juju()

    def get_apps(self, model_names: Iterable[str] | None = None) -> dict[str, AppStatus]:
        """Get applications.

        Args:
            model_names:
                Get all applications that belong to the provided model names.
                If no model names are provided, then all applications are returning.

        Raises:
            TooManyDeployedApplications:
                Raised if multiple applications share the same name in the returned
                ``model_names`` search.
        """
        models = [self.models[m] for m in model_names] if model_names else self.models.values()

        result: dict[str, AppStatus] = {}
        for model in models:
            apps = model.status().apps
            if intersection := set(result) & set(apps):
                raise TooManyDeployedAppsError(
                    f"App name(s) '{intersection}' {'is' if len(intersection) == 1 else 'are'} "
                    f"used multiple times in the current testing context. Either narrow your "
                    f"application name search or ensure that you use a unique name for each "
                    f"deployed application."
                ) from None

            result.update(apps)

        return result

    def get_app(self, app_name: str, /, *, model_name: str | None = None) -> AppStatus:
        """Get an application.

        Args:
            app_name: Name of the application.
            model_name: Name of the model the application is deployed to.

        Raises:
            AppNotFoundError:
                Raised if the requested application is not found in any model.
            TooManyDeployedAppsError:
                Raised if multiple applications share the same name in the current
                testing context and no ``model_name`` was provided.
        """
        args = []
        if model_name:
            args.append(model_name)

        apps = self.get_apps(*args)
        try:
            return apps[app_name]
        except KeyError:
            raise AppNotFoundError(
                f"App not found: '{app_name}' is not deployed"
                f"{f' in model \'{model_name}\'' if model_name else ''}."
                f"Available apps: {', '.join(f'{app_}' for app_ in apps)}"
            ) from None

    def get_models(self, model_names: Iterable[str] | None = None) -> dict[str, Juju]:
        """Get models.

        Args:
            model_names: Models to retrieve.

        Raises:
            ModelNotFoundError: Raised if a provided model name does not exist.
        """
        if model_names:
            return {model: self.models[model] for model in model_names}
        else:
            return dict(self.models)

    def get_units(self, model_names: Iterable[str] | None = None) -> dict[str, UnitStatus]:
        """Get units.

        Args:
            model_names:
                Get all units that belong to the provided model names.
                If no model names are provided, then all applications are returning.

        Raises:
            TooManyDeployedApplications:
                Raised if multiple applications share the same name in the returned
                ``model_names`` search.
        """
        apps = self.get_apps(model_names)
        return {name: unit for app in apps.values() for name, unit in app.units.items()}

    def get_unit(self, unit_name: str, /, *, model_name: str | None = None) -> UnitStatus:
        """Get a unit.

        Args:
            unit_name: Name of the unit.
            model_name: Name of the model the unit is deployed in.

        Raises:
            TooManyDeployedAppsError:
                Raised if multiple applications share the same name in the current
                testing context and no ``model_name`` was provided.
            UnitNotFoundError:
                Raised if the requested unit is not found under its application namespace.
        """
        args = []
        if model_name:
            args.append(model_name)

        units = self.get_units(*args)
        try:
            return units[unit_name]
        except KeyError:
            raise UnitNotFoundError(
                f"Unit not found: '{unit_name}' is not deployed"
                f"{f' in model \'{model_name}\'' if model_name else ''}. "
                f"Available units: {', '.join(f'{unit_}' for unit_ in units)}"
            ) from None
