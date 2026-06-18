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

"""Track and control behavior-driven development (BDD) testing contexts."""

import secrets
import time
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from jubilant import Juju, Task
from jubilant.statustypes import AppStatus, UnitStatus

from ._constants import DEFAULT_WAIT_TIMEOUT
from ._errors import (
    AppNotFoundError,
    ModelNotFoundError,
    TooManyDeployedAppsError,
    UnitNotFoundError,
    WaitError,
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

    def destroy(self, *models: str, **kwargs: Any) -> None:
        """Destroy model(s) in the testing context.

        Args:
            models:
                Names of model(s) to destroy. If no model names are provided,
                then all models will be destroyed.
            kwargs: Keyword arguments to pass to the :meth:`Juju.destory_model` method.

        Keyword Args:
            destroy_storage: If ``True``, destroy all storage instances in the model(s).
            force: If ``True``, force model destruction and ignore errors.
        """
        for model in models or self.keys():
            self[model].destroy_model(model, **kwargs)

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
        wait_timeout:
            The default timeout for :meth:`wait` (in seconds)
            if that method's ``timeout`` parameter is not specified.
        action_results: Stack that tracks the results of ``juju run``.
        exec_results: Stack that tracks the results of ``juju exec``.
        models: Mapping that tracks models in the testing context.
    """

    wait_timeout: float = DEFAULT_WAIT_TIMEOUT
    action_results: stack[Task] = field(default_factory=stack, init=False)
    exec_results: stack[Task] = field(default_factory=stack, init=False)
    models: ModelMapping = field(default_factory=ModelMapping, init=False)

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

    def wait(
        self,
        ready: Callable[["Context"], bool],
        *,
        error: Callable[["Context"], bool] | None = None,
        delay: float = 1.0,
        timeout: float | None = None,
        successes: int = 3,
    ) -> None:
        """Wait until ``ready(context)`` returns ``True``.

        This method will repeatably poll the existing context (waiting *delay* seconds between
        each call), and will successfully exit after the *ready* callable returns ``True`` for
        *successes* times in a row.

        Args:
            ready:
                Callable that takes a :class:`Context` object and returns ``True`` when the
                wait should be considered ready. The callable must return ``True`` *successes*
                times in a row before ``wait`` will return.
            error:
                Callable that takes a :class:`Context` object and returns ``True`` when ``wait``
                should raise an error (:class:`WaitError`).
            delay: Delay in seconds between :class:`Context` polls.
            timeout:
                Overall timeout in seconds; :class:`TimeoutError` is raised if this
                is reached. If not specified, uses the *wait_timeout* specified when the
                testing context was created.
            successes: Number of times *ready* must return ``True`` for the wait to succeed.

        Raises:
            TimeoutError:
                If the *timeout* is reached. A string representation
                of the last status, if any, is added as an exception note.
            WaitError:
                If the *error* callable returns ``True``. A string representation
                of the last status is added as an exception note.
        """
        if timeout is None:
            timeout = self.wait_timeout

        success_count = 0
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            if error is not None and error(self):
                name = getattr(error, "__qualname__", repr(error))
                raise WaitError(f"Wait error function '{name}' returned `True`")

            if ready(self):
                success_count += 1
                if success_count >= successes:
                    return
            else:
                success_count = 0

            time.sleep(delay)

        name = getattr(ready, "__qualname__", repr(ready))
        raise TimeoutError(f"Wait timed out for function '{name}' after {timeout}s")
