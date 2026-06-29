## Overview

This project is a `pytest` plugin that provides reusable Gherkin step
handlers for behavior-driven testing of Juju charmed operators, built on top
of `jubilant` and `pytest-bdd`. Source lives in
`src/pytest_jubilant_bdd/`; tests live in `tests/`.

The project uses:

- `uv` for dependency management and packaging.
- `just` as the task runner (see `justfile`).
- `ruff` for formatting and linting.
- `pyright` for static type checking.
- `coverage.py` for test coverage with branch coverage on `src/**/*.py`.

Private modules use the `_`-prefix convention (for example, `_main.py`,
`_context.py`, `_assertions.py`). The public API is re-exported through
`src/pytest_jubilant_bdd/__init__.py`. Consumers and tests import from the
package root, not from private modules.

## Code style

Follow PEP 8 and PEP 257, plus:

### Imports

Three groups, alphabetized (`ruff format` handles ordering): standard
library, third-party, `pytest_jubilant_bdd`.

### Docstrings

Every public module, class, and function must have a PEP 257 docstring.
Public modules declare `__all__` to make the public API explicit.

### Private modules

Internal modules use the `_`-prefix convention. The public API is
re-exported through `src/pytest_jubilant_bdd/__init__.py`. Error-path
tests that need to call handler functions directly may import from
`pytest_jubilant_bdd._main` (this is the documented exception to the rule;
see the `unit-testing` SKILL.md).

### Type annotations

All function signatures must have explicit type annotations. `just typecheck`
(pyright) validates them.

If a typing issue is found in production code (`src/pytest_jubilant_bdd/`),
STOP and propose a resolution to the human-in-the-loop before editing
production code:

1. Describe the issue, its location, and the impact.
2. Propose a concrete fix.
3. Ask whether to proceed with the proposed fix or to research alternative
   resolutions.

Do not edit production code until the user explicitly approves the fix.

### Avoid inline error handling

```python
if path is None:
    env_var = app.upper().replace("-", "_") + "_CHARM_PATH"
    try:
        path = Path(os.environ[env_var])
    except KeyError:
        raise CharmNotFoundError(...) from None
```

Not:

```python
path = Path(os.environ[app.upper().replace("-", "_") + "_CHARM_PATH"]) if env_var in os.environ else None
```

Use explicit `raise` statements and intermediate variables for error
handling rather than burying the logic in one-liners or ternary
expressions.

### Comments

Do __not__ add generic one-off comments throughout the main codebase. Do
add comments in test files to provide justifications for assertions,
mocks, and workarounds.

## Build commands

```bash
just build      # Build wheel and sdist into dist/ via `uv build`.
just clean      # Remove .venv, build artifacts, __pycache__, *.pyc.
just setup      # Create a uv dev environment (`uv sync --extra dev`).
just lock       # Regenerate uv.lock.
just upgrade    # Upgrade uv.lock with the latest dependencies.
```

## Testing

```bash
just check          # Run all static checks (`fmt`, `lint`, `typecheck`).
just unit           # Run unit tests with coverage report.
just integration    # Run integration tests.
just test           # Run all test suites (unit + integration).
just test <target>  # Run a specific test target.
just fmt            # Format all Python source code with ruff.
just lint           # Lint with ruff (no auto-fix).
just typecheck      # Static type checking with pyright.
```

### Coverage

The target is **90% branch coverage** on `src/**/*.py`. Do __not__ write
unit tests for code paths that are impossible to reach in production.

## Development workflow

1. Write Python code in `src/pytest_jubilant_bdd/`.
2. Write matching unit tests in `tests/unit/`. Reference the
   `unit-testing` SKILL.md file at `.agents/skills/unit-testing/SKILL.md`
   for detailed instructions on writing unit tests for reusable Gherkin
   step handlers, including test class structure, fixtures, error-path
   conventions, and the `%...%` block syntax used by `flexible`
   parsers.
3. Run `just unit` -- ensure all tests pass and coverage meets the 90%
   branch coverage threshold.
4. Format: `just fmt`.
5. Lint: `just lint` (uses `ruff check`). Fix all linter errors.
6. Typecheck: `just typecheck` (uses `pyright`). Fix all typing
   errors. If a typing issue is in production code, follow the
   human-in-the-loop protocol in the Code style section above.
7. Repeat for each new or modified file.

Pipe the output of shell commands to either `head` or `tail` to
capture the `stdout` and/or `stderr`.

## Commit conventions

Use Conventional Commits prefixes for commit messages:

- `feat:` -- New user-facing feature.
- `fix:` -- Bug fix.
- `test:` -- Add or modify tests only.
- `chore:` -- Maintenance tasks (formatting, dependency updates, etc.).
- `docs:` -- Documentation only.
- `refactor:` -- Code change that neither fixes a bug nor adds a feature.

Scopes are allowed (for example, `chore(deps):`, `chore(fmt):`).

### Commit trailers

- Commits must be signed off (`Signed-off-by:` trailer) **by the human**.
  Agents must never add a `Signed-off-by:` trailer on the human's behalf.
- Agents must include an `Assisted-by:` trailer identifying the agent
  and model.
- Order trailers as: `Assisted-by:` first, then the human's
  `Signed-off-by:` last (added by the human).

Format:

    Assisted-by: AGENT_NAME:MODEL_VERSION:[MODEL_VARIANT]

- `AGENT_NAME`: The AI tool (for example, `opencode`).
- `MODEL_VERSION`: The specific model version used.
- `MODEL_VARIANT`: The variant of the model version used (for example,
  `low`, `medium`, or `high`). Optional.

Other rules:

- Commit messages must be ASCII only.
- Keep PRs small and focused.
- Maintain a linear git history.

### Constraints

- Do __not__ add new dependencies beyond what is already in
  `pyproject.toml` without approval.
- Do __not__ install anything with `apt` or `snap`.
- Do __not__ run commands that require `sudo`.
- Do __not__ edit production code (`src/pytest_jubilant_bdd/`) without
  explicit user approval -- propose the change first and wait for
  approval.
- All errors must be handled explicitly in Python code.
