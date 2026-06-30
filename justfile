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

uv := require("uv")

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"

uv_run := "uv run --frozen --extra dev"

[private]
default:
    @just help

# Prepare the local environment
setup: env

# Clean project directory
clean:
    rm -rf .venv build dist *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Apply static checks
check: fmt lint typecheck

# Run tests for specified targets, or all tests if none specified
test *targets:
    #!/usr/bin/env bash
    if [ "{{targets}}" = "" ]; then
        just test-all
        exit 0
    fi

    for target in {{targets}}; do
        if just --show $target > /dev/null 2>&1; then
            echo "Running $target tests..."
            just $target
        else
            echo "$target tests not found, skipping."
            exit 1
        fi
    done

# Run all test suites
test-all: unit

# Run unit tests
unit *args:
    {{uv_run}} coverage run -m pytest --tb native -v -s {{args}} tests/unit
    {{uv_run}} coverage report
    {{uv_run}} coverage xml -o {{justfile_directory() / "cover" / "coverage.xml"}}

# Build project artifacts
build:
    uv build

# Regenerate uv.lock
lock:
    uv lock

# Create a uv development environment
env: lock
    uv sync --extra dev

# Upgrade uv.lock with the latest dependencies
upgrade:
    uv lock --upgrade

# Apply formatting standards
fmt:
    {{uv_run}} ruff format
    {{uv_run}} ruff check --fix

# Check files against style standards
lint:
    {{uv_run}} ruff check

# Perform type checking
typecheck:
    {{uv_run}} pyright

# Show available recipes
help:
    @just --list --unsorted
