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
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py seed_sample_data
```

The seed command is safe to run repeatedly. It creates 12 books, downloads their
cover images from the [Open Library Covers API](https://openlibrary.org/dev/docs/api/covers),
and creates five non-login sample authors with between one and five reviews for
each book. Internet access is required for cover downloads. Use
`uv run python manage.py seed_sample_data --offline` to generate placeholder PNG
covers when working without a network connection.

## Run locally

Run the development server inside the devcontainer:

```bash
uv run python manage.py runserver 0.0.0.0:8000
```

Then open <http://localhost:8000/> on the host.

## HTTP endpoints

The book views show a paginated catalog and each book's reviews. Signed-in users
can submit one review per book with a rating from 0 through 10. The
authentication views use Django's built-in credential validation and session
authentication.

| Method | URL | Arguments | Return value |
| --- | --- | --- | --- |
| `GET` | `/` | Optional `q` and `page` query parameters | `200 OK` with title search, average ratings, and up to 10 books with previous/next controls |
| `GET` | `/signup/` | None | `200 OK` with the signup form |
| `POST` | `/signup/` | `username`, `password1`, `password2` | Creates and signs in the user, then redirects to `/`; invalid input redisplays the form |
| `GET` | `/login/` | None | `200 OK` with the login form |
| `POST` | `/login/` | `username`, `password` | Signs in the user, then redirects to `/`; invalid input redisplays the form |
| `POST` | `/logout/` | None | Signs out the user, then redirects to `/` |
| `GET` | `/books/<book_id>/` | `book_id`: UUID path parameter | `200 OK` with the book, its reviews, and the review form |
| `POST` | `/books/<book_id>/` | `rating`, `text` | Creates the signed-in user's review and redirects back to the book |
| `GET` | `/books/<book_id>/cover/` | `book_id`: UUID path parameter | `200 OK` with the book's JPEG or PNG cover |

`/books/<book_id>/` returns `404 Not Found` when `book_id` is not a valid UUID or
does not identify an existing book. Review ratings outside 0 through 10, blank
text, and duplicate reviews are redisplayed with validation errors and are not
saved.
