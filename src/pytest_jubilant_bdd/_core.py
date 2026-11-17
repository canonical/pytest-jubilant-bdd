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

"""Core utilities used within ``pytest-jubilant-bdd``."""

__all__ = ["cli"]

import logging
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path

logger = logging.getLogger("pytest-jubilant-bdd")


def cli(
    root: str,
    /,
    *args: str,
    stdin: str | None = None,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    cwd: Path | str | None = None,
    stream: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a command through the host's CLI and stream its output to the user's console.

    Args:
        root: The root command to call.
        args: Arguments to pass to the root command.
        stdin: Standard input to pipe into the root command.
        check: If ``True``, raise :class:`subprocess.CalledProcessError` when
            the command exits with a non-zero exit code.
        env: Environment variables to pass to the root command. If ``None``,
            the current process's environment is used.
        cwd: Working directory to run the root command in. If ``None``, the
            current working directory is used.
        stream:
            If ``True``, the command inherits the ``stdout`` and ``stderr``
            streams of the ``pytest`` process, streaming its output to the
            user's console as the command runs. If ``False``, the command's
            output is captured, logged, and returned on the completed process
            object.

    Returns:
        The completed process. When ``stream=False``, ``stdout`` and ``stderr``
        hold the captured output. When ``stream=True``, both are ``None`` as
        the output was streamed to the user's console instead.

    Raises:
        FileNotFoundError:
            Raised if the root command is not found on the host.
        subprocess.CalledProcessError:
            Raised if the command exits with a non-zero exit code and
            ``check`` is ``True``.
    """
    cmd = [root, *args]
    log_cmd = shlex.join(cmd)

    logger.info("running command: %s", log_cmd)
    if stream:
        result = subprocess.run(cmd, input=stdin, check=False, cwd=cwd, env=env, text=True)
    else:
        result = subprocess.run(
            cmd, input=stdin, check=False, capture_output=True, cwd=cwd, env=env, text=True
        )

    _log_command_result(log_cmd, result.returncode, result.stdout, result.stderr, check=check)

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )

    return result


def _log_command_result(
    log_cmd: str,
    returncode: int,
    stdout: str | None,
    stderr: str | None,
    *,
    check: bool,
) -> None:
    """Log the outcome of a command invoked by :func:``cli``.

    Args:
        log_cmd: The command, in shell-quoted form.
        returncode: The exit code the command exited with.
        stdout: Captured standard output, or ``None`` if not captured.
        stderr: Captured standard error, or ``None`` if not captured.
        check: Whether a non-zero exit code is considered a failure.

    Notes:
        - If ``check=True``, commands that return a non-zero exit code will be
          logger as ``ERROR`` and not ``DEBUG``.
    """
    failed = returncode != 0 and check
    outcome = "failed" if failed else "completed"
    message = "command '%s' %s with exit code %s"
    log_args: list[str | int] = [log_cmd, outcome, returncode]

    if stdout:
        message += "\nstdout: %s"
        log_args.append(stdout)

    if stderr:
        message += "\nstderr: %s"
        log_args.append(stderr)

    if failed:
        logger.error(message, *log_args)
    else:
        logger.debug(message, *log_args)
