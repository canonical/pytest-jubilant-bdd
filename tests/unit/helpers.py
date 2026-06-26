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

"""Helper functions used in the ``pytest-jubilant-bdd`` unit tests."""

import json

# ---
# Mocked `juju status --format json` output for unit tests.
# ---

# JSON template for a single application with a relation to another app.
_STATUS_APP_TEMPLATE = {
    "application-status": {"current": "active"},
    "base": {"channel": "24.04", "name": "ubuntu"},
    "charm": "slurmctld",
    "charm-channel": "latest/stable",
    "charm-name": "slurmctld",
    "charm-origin": "charmhub",
    "charm-rev": 1,
    "exposed": False,
    "units": {
        "slurmctld/0": {
            "juju-status": {"current": "idle"},
            "workload-status": {"current": "active"},
        }
    },
}

# JSON template for the model section of `juju status` output.
_STATUS_MODEL_TEMPLATE = {
    "name": "test-xyz123",
    "type": "iaas",
    "controller": "test-controller",
    "cloud": "localhost",
    "version": "3.6.0",
    "model-status": {"current": "available"},
}


def make_status_json(
    apps: dict[str, dict] | None = None,
    *,
    model_name: str = "test-xyz123",
) -> str:
    """Build a mocked ``juju status --format json`` payload.

    Args:
        apps: Mapping of app name to its status dict. If ``None``, an empty
            applications dict is used.
        model_name: Name of the model in the status payload.

    Returns:
        A JSON string suitable for ``mock_subprocess_run.return_value.stdout``.
    """
    model = dict(_STATUS_MODEL_TEMPLATE)
    model["name"] = model_name
    return json.dumps(
        {
            "applications": apps or {},
            "machines": {},
            "model": model,
        }
    )


def make_app_with_relation(
    app_name: str = "slurmctld",
    related_app: str = "slurmd",
    interface: str = "slurmd",
) -> dict:
    """Build a status dict for an app that has a relation to another app.

    Args:
        app_name: Name of the application.
        related_app: Name of the related application.
        interface: Name of the relation interface.

    Returns:
        A dict suitable for use as a value in the ``applications`` mapping
        passed to :func:`make_status_json`.
    """
    app = json.loads(json.dumps(_STATUS_APP_TEMPLATE))  # deep copy
    app["charm"] = app_name
    app["charm-name"] = app_name
    app["units"] = {
        f"{app_name}/0": {
            "juju-status": {"current": "idle"},
            "workload-status": {"current": "active"},
        }
    }
    app["relations"] = {
        f"{app_name}:server": [
            {
                "related-application": related_app,
                "interface": interface,
            }
        ]
    }
    return app


def make_app_without_relation(app_name: str = "slurmctld") -> dict:
    """Build a status dict for an app with no relations.

    Args:
        app_name: Name of the application.

    Returns:
        A dict suitable for use as a value in the ``applications`` mapping
        passed to :func:`make_status_json`.
    """
    app = json.loads(json.dumps(_STATUS_APP_TEMPLATE))  # deep copy
    app["charm"] = app_name
    app["charm-name"] = app_name
    app["units"] = {
        f"{app_name}/0": {
            "juju-status": {"current": "idle"},
            "workload-status": {"current": "active"},
        }
    }
    app["relations"] = {}
    return app


# ---
# Mocked `juju run` / `juju exec` JSON output for unit tests.
# ---

# JSON template for a single `Task` object returned by `juju run` or
# `juju exec`. The outer dict is keyed by the unit or machine name.
_TASK_TEMPLATE = {
    "id": "1",
    "status": "completed",
    "results": {},
    "return-code": 0,
}


def make_task_json(
    target: str = "slurmctld/0",
    *,
    task_id: str = "1",
    status: str = "completed",
    return_code: int = 0,
    results: dict | None = None,
) -> str:
    """Build a mocked ``juju run`` / ``juju exec`` JSON payload.

    Args:
        target: Name of the unit or machine that the task ran on. This is
            used as the outer dict key.
        task_id: Task ID string.
        status: Task status (e.g., ``"completed"``, ``"failed"``).
        return_code: Return code from the action/exec command.
        results: Results dict from the action. Defaults to an empty dict.

    Returns:
        A JSON string suitable for ``mock_subprocess_run.return_value.stdout``.
    """
    task = dict(_TASK_TEMPLATE)
    task["id"] = task_id
    task["status"] = status
    task["return-code"] = return_code
    task["results"] = results if results is not None else {}
    return json.dumps({target: task})
