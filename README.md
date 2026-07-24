# bookkin

A Django web application.

## Environment

- Python 3.13+
- Managed with [uv](https://docs.astral.sh/uv/)
- Runs in a devcontainer (`.devcontainer/`)

## Tools

- ruff — formatting & linting
- coverage — test coverage

## Setup

```bash
uv sync
```

## Run locally

Run the development server inside the devcontainer:

```bash
uv run python manage.py runserver 0.0.0.0:8000
```

Then open <http://localhost:8000/> on the host.

## HTTP endpoints

The first views are placeholders and return plain-text responses.

| Method | URL | Arguments | Return value |
| --- | --- | --- | --- |
| `GET` | `/` | None | `200 OK` with the application home page |
| `GET` | `/books/` | None | `200 OK` with the book list |
| `GET` | `/books/<book_id>/` | `book_id`: UUID path parameter | `200 OK` with the requested book ID |

`/books/<book_id>/` returns `404 Not Found` when `book_id` is not a valid UUID.
