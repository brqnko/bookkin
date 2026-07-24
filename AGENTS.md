# Agent guide

This file applies to the entire repository. Add a more specific `AGENTS.md` in a
subdirectory only when that area develops conventions that genuinely differ from
these.

## Current state

`bookkin` is a Django project scaffold, not yet a generated Django site. At
present there is no `manage.py`, settings module, application package, database
schema, or domain model. Treat those omissions as undecided design, not as files
to reconstruct from convention.

- `pyproject.toml` and `uv.lock` are the dependency sources of truth.
- Python 3.13 and `uv` are the supported toolchain.
- The devcontainer mounts the repository at `/workspace`; commands below also
  work from the repository root on a host with `uv`.
- Do not assume a database, queue, cache, API framework, frontend stack, or
  deployment target until the repository or the task establishes one.

If a task depends on a missing foundational decision with lasting consequences,
surface that decision instead of silently introducing an architecture. Small,
reversible choices may use the simplest Django-native option.

## Working agreement

Before changing code:

1. Read the relevant source, tests, configuration, and documentation.
2. Check `git status` and preserve unrelated user changes.
3. Keep the patch scoped to the requested behavior; avoid opportunistic
   scaffolding or dependencies.

While changing code:

- Follow existing patterns once they exist. Until then, prefer standard Django
  structure and the smallest design that leaves room for later decisions.
- Put project configuration in `config/` and domain behavior in focused Django
  apps. Do not create a catch-all app such as `core` unless it has a clear role.
- Keep views thin. Put reusable queries on querysets/managers and reusable
  domain operations in clearly named modules or model methods.
- Use Django forms, validators, permissions, transactions, and ORM expressions
  before duplicating their behavior.
- Treat migrations as part of a model change. Generate schema migrations with
  Django, review them, and do not hand-edit generated migrations unless the
  change specifically requires a data or custom migration.
- Add or update tests with behavior changes. Prefer tests that exercise public
  behavior over implementation details.
- Keep secrets and environment-specific values out of source control. Never
  weaken security settings merely to make a check pass.
- Update the README when setup steps, required services, environment variables,
  or user-facing commands change.

## Dependencies

Bootstrap the locked environment with:

```bash
uv sync --frozen
```

Use `uv add <package>` for runtime dependencies and `uv add --dev <package>` for
development-only dependencies. Do not edit `uv.lock` manually. A dependency
addition should be justified by the task and used by the resulting patch.

Run project commands through `uv run` so they use the locked environment. Do not
activate `.venv` in scripts or documentation.

## Validation

Run the smallest relevant checks while iterating, then the complete available
baseline before handing off:

```bash
uv run ruff format --check .
uv run ruff check .
```

Once `manage.py` exists, also run:

```bash
uv run python manage.py check
uv run python manage.py test
uv run python manage.py makemigrations --check --dry-run
```

For coverage-sensitive work, use:

```bash
uv run coverage run manage.py test
uv run coverage report
```

If a command is unavailable because the project is still pre-scaffold, say so
explicitly; do not report it as passing. If a check fails for an unrelated,
pre-existing reason, record the exact failure and still run all other useful
checks.

Before completion, review `git diff --check` and the final diff. Report:

- what changed and why;
- tests and checks actually run, with outcomes;
- any migrations, dependency changes, or unresolved decisions.

Do not claim completion when required migrations are missing, tests are failing
because of the patch, or documented setup no longer works.
