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

"""Reusable assertions for validating the behavior of charms."""

__all__ = ["assertions"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._constants import AgentStatus, WorkloadStatus

if TYPE_CHECKING:
    from ._context import Context


class AppAssertions:
    """Reusable application-level assertions."""

    @staticmethod
    def all_agent_statuses_are(
        context: "Context", *apps: str, expected: AgentStatus
    ) -> bool:
        """Validate the status of all agents in an application.

        Args:
            context: Reference to the current testing :class:`Context` object.
            apps: Applications to assess the agent status of.
            expected: The expected agent status.

        Returns:
            ``True`` if all the agent's statuses in ``apps`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for app in context.get_apps(*apps).values():
            for unit in app.units.values():
                if unit.juju_status.current != expected:
                    return False

        return True

    @staticmethod
    def all_unit_statuses_are(
        context: "Context", *apps: str, expected: WorkloadStatus
    ) -> bool:
        """Validate the status of all units in an application.

        Args:
            context: Reference to the current testing :class:`Context` object.
            apps: Applications to assess the unit status of.
            expected: The expected unit status.

        Returns:
            ``True`` if all the unit's statuses in ``apps`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for app in context.get_apps(*apps).values():
            for unit in app.units.values():
                if unit.workload_status.current != expected:
                    return False

        return True

    @staticmethod
    def all_unit_status_messages_are(
        context: "Context", *apps: str, expected: str
    ) -> bool:
        """Validate the status message of all units in an application.

        Args:
            context: Reference to the current testing :class:`Context` object.
            apps: Applications to assess the unit status message of.
            expected: The expected unit status message.

        Returns:
            ``True`` if all the unit's status messages in ``apps`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for app in context.get_apps(*apps).values():
            for unit in app.units.values():
                if unit.workload_status.message != expected:
                    return False

        return True


class ModelAssertions:
    """Reusable model-level assertions."""

    @staticmethod
    def all_agent_statuses_are(
        context: "Context", *models: str, expected: AgentStatus
    ) -> bool:
        """Validate the status of all agents in a model.

        Args:
            context: Reference to the current testing :class:`Context` object.
            models: Models to assess the agent status of.
            expected: The expected agent status.

        Returns:
            ``True`` if all the agent's statuses in ``models`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for model in context.get_models(*models):
            for app in context.get_apps(model=model).values():
                for unit in app.units.values():
                    if unit.juju_status.current != expected:
                        return False

        return True

    @staticmethod
    def all_app_statuses_are(
        context: "Context", *models: str, expected: WorkloadStatus
    ) -> bool:
        """Validate the status of all applications in a model.

        Args:
            context: Reference to the current testing :class:`Context` object.
            models: Models to assess the application status of.
            expected: The expected application status.

        Returns:
            ``True`` if all the application's statuses in ``models`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for model in context.get_models(*models):
            for app in context.get_apps(model=model).values():
                if app.app_status.current != expected:
                    return False

        return True

    @staticmethod
    def all_app_status_messages_are(
        context: "Context", *models: str, expected: str
    ) -> bool:
        """Validate the status message of all applications in a model.

        Args:
            context: Reference to the current testing :class:`Context` object.
            models: Models to assess the application status message of.
            expected: The expected application status message.

        Returns:
            ``True`` if all the application's status messages in ``models`` are equal
            to ``expected``, otherwise, returns ``False``.
        """
        for model in context.get_models(*models):
            for app in context.get_apps(model=model).values():
                if app.app_status.message != expected:
                    return False

        return True

    @staticmethod
    def all_unit_statuses_are(
        context: "Context", *models: str, expected: WorkloadStatus
    ) -> bool:
        """Validate the status of all units in a model.

        Args:
            context: Reference to the current testing :class:`Context` object.
            models: Models to assess the unit status of.
            expected: The expected unit status.

        Returns:
            ``True`` if all the unit's statuses in ``models`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for model in context.get_models(*models):
            for app in context.get_apps(model=model).values():
                for unit in app.units.values():
                    if unit.workload_status.current != expected:
                        return False

        return True

    @staticmethod
    def all_unit_status_messages_are(
        context: "Context", *models: str, expected: str
    ) -> bool:
        """Validate the status message of all units in a model.

        Args:
            context: Reference to the current testing :class:`Context` object.
            models: Models to assess the unit status message of.
            expected: The expected unit status message.

        Returns:
            ``True`` if all the unit's status messages in ``models`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for model in context.get_models(*models):
            for app in context.get_apps(model=model).values():
                for unit in app.units.values():
                    if unit.workload_status.message != expected:
                        return False

        return True


@dataclass(frozen=True)
class Assertions:
    """Reusable assertions for validating the behavior of charms."""

    app: AppAssertions = AppAssertions()
    model: ModelAssertions = ModelAssertions()


assertions = Assertions()
