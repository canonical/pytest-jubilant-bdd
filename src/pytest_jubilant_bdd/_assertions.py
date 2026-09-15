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

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._constants import AgentStatus, WorkloadStatus

if TYPE_CHECKING:
    from ._context import Context


class AppAssertions:
    """Reusable application-level assertions."""

    @staticmethod
    def all_agent_statuses_are(context: "Context", *apps: str, expected: AgentStatus) -> bool:
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
    def all_unit_statuses_are(context: "Context", *apps: str, expected: WorkloadStatus) -> bool:
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
    def all_unit_status_messages_are(context: "Context", *apps: str, expected: str) -> bool:
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
    def all_agent_statuses_are(context: "Context", *models: str, expected: AgentStatus) -> bool:
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
    def all_app_statuses_are(context: "Context", *models: str, expected: WorkloadStatus) -> bool:
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
    def all_app_status_messages_are(context: "Context", *models: str, expected: str) -> bool:
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
    def all_unit_statuses_are(context: "Context", *models: str, expected: WorkloadStatus) -> bool:
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
    def all_unit_status_messages_are(context: "Context", *models: str, expected: str) -> bool:
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


class StorageAssertions:
    """Reusable storage-level assertions."""

    @staticmethod
    def instances_are_attached(
        context: "Context",
        storage: str,
        unit: str,
        *,
        count: int,
        model: str | None = None,
    ) -> bool:
        """Validate that a number of storage instances are attached to a unit.

        Args:
            context: Reference to the current testing :class:`Context` object.
            storage: Name of the storage (as defined in the charm's metadata)
                to assess the attachment status of.
            unit: Unit that the storage instances should be attached to.
            count: The minimum number of storage instances that should be
                attached to ``unit``.
            model: Name of the model to search for the storage in. If ``None``,
                the current model is used.
        """
        juju = context.get_juju(model)

        # `juju storage` outputs nothing when the model has no storage, so guard
        # against an empty payload before parsing.
        output = juju.cli("storage", "--format", "json")
        storages = json.loads(output).get("storage", {}) if output.strip() else {}

        attached = 0
        for storage_id, info in storages.items():
            label, _, _ = storage_id.partition("/")
            if label != storage:
                continue
            if info["status"]["current"] != "attached":
                continue
            attachments = info.get("attachments")
            if attachments is None:
                continue
            if unit not in attachments["units"]:
                continue
            attached += 1

        return attached >= count


class UnitAssertions:
    """Reusable unit-level assertions."""

    @staticmethod
    def all_agent_statuses_are(context: "Context", *units: str, expected: AgentStatus) -> bool:
        """Validate the status of all agents in a set of units.

        Args:
            context: Reference to the current testing :class:`Context` object.
            units: Units to assess the agent status of.
            expected: The expected agent status.

        Returns:
            ``True`` if all the agent's statuses in ``units`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for unit in context.get_units(*units).values():
            if unit.juju_status.current != expected:
                return False

        return True

    @staticmethod
    def all_statuses_are(context: "Context", *units: str, expected: WorkloadStatus) -> bool:
        """Validate the workload status of all units in a set of units.

        Args:
            context: Reference to the current testing :class:`Context` object.
            units: Units to assess the workload status of.
            expected: The expected workload status.

        Returns:
            ``True`` if all the workload statuses in ``units`` are equal to ``expected``,
            otherwise, returns ``False``.
        """
        for unit in context.get_units(*units).values():
            if unit.workload_status.current != expected:
                return False

        return True

    @staticmethod
    def all_status_messages_are(context: "Context", *units: str, expected: str) -> bool:
        """Validate the workload status message of all units in a set of units.

        Args:
            context: Reference to the current testing :class:`Context` object.
            units: Units to assess the workload status message of.
            expected: The expected workload status message.

        Returns:
            ``True`` if all the workload status messages in ``units`` are equal to
            ``expected``, otherwise, returns ``False``.
        """
        for unit in context.get_units(*units).values():
            if unit.workload_status.message != expected:
                return False

        return True


@dataclass(frozen=True)
class Assertions:
    """Reusable assertions for validating the behavior of charms."""

    app: AppAssertions = AppAssertions()
    model: ModelAssertions = ModelAssertions()
    storage: StorageAssertions = StorageAssertions()
    unit: UnitAssertions = UnitAssertions()


assertions = Assertions()
