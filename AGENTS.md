# Agent guide

This file applies to the entire repository. Add a more specific `AGENTS.md` in a
subdirectory only when that area develops conventions that genuinely differ from
these.

## Current state

`bookkin` is a server-rendered Django web application for browsing books and
submitting reader reviews.

- Project configuration lives in `config/`; the `bookkin/` app contains the
  domain models, forms, views, URLs, templates, static CSS, tests, and sample-data
  command.
- SQLite is the current database. `Book` stores its cover image as binary data,
  and `Review` belongs to a book and Django authentication user. The migrations
  in `bookkin/migrations/` are the schema history.
- The UI provides a searchable, paginated catalog, book details, authentication,
  and one review per signed-in user and book. It uses Django templates and
  responsive CSS without a JavaScript or HTMX frontend.
- `seed_sample_data` creates the demonstration catalog and supports both
  downloaded and offline-generated cover images.
- The current production path is a Docker image running Gunicorn and WhiteNoise
  behind an nginx TLS-terminating proxy, with SQLite stored on a persistent
  volume. See `README.md` and `infra/Dockerfile`.
- `pyproject.toml` and `uv.lock` are the dependency sources of truth.
- Python 3.13 and `uv` are the supported toolchain.
- The devcontainer mounts the repository at `/workspace`; commands below also
  work from the repository root on a host with `uv`.
- There is no queue, cache, API framework, or client-side application. Do not
  introduce one unless the task establishes the need.

Changes to the database engine, binary cover storage, frontend architecture, or
deployment topology are foundational decisions. Surface them instead of
silently replacing the current design. Small, reversible choices may use the
simplest Django-native option.

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
- Add concise comments for Django-specific behavior that may not be obvious to
  a developer familiar with general web development. Explain what the framework
  does automatically and when it happens; do not restate the code or explain
  general Python and database concepts.
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

Also run:

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

If a command is unavailable in the current environment, say so explicitly; do
not report it as passing. If a check fails for an unrelated, pre-existing reason,
record the exact failure and still run all other useful checks.

Before completion, review `git diff --check` and the final diff. Report:

- what changed and why;
- tests and checks actually run, with outcomes;
- any migrations, dependency changes, or unresolved decisions.

Do not claim completion when required migrations are missing, tests are failing
because of the patch, or documented setup no longer works.
