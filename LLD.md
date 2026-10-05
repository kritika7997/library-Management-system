# Low-Level Design

## Technology

- Frontend: HTML, CSS, browser JavaScript
- Backend: Python and FastAPI
- Request models: Pydantic
- Database: SQLite 3 via Python's `sqlite3` module

## Frontend

- `static/index.html` defines the add-book form, collection area, count, search input, and status message.
- `static/styles.css` defines the page layout, colors, typography, responsive behavior, and book-row states.
- `static/app.js` loads books, renders rows, filters the loaded list, submits new books, and updates availability.
- The frontend sends JSON requests to the same-origin `/api/books` endpoints.

## Backend Models

### `BookCreate`

- `title`: required string, 1-200 characters
- `author`: optional string, up to 200 characters; defaults to an empty string
- `isbn`: optional string, up to 32 characters; defaults to an empty string

### `AvailabilityUpdate`

- `is_available`: required boolean

## Database

Table: `books`

| Column | SQLite type | Rules / default |
|---|---|---|
| `id` | INTEGER | Primary key, autoincrement |
| `title` | TEXT | Required |
| `author` | TEXT | Required, defaults to an empty string |
| `isbn` | TEXT | Required, defaults to an empty string |
| `is_available` | INTEGER | Required, defaults to `1` (available) |

The API converts the stored integer availability value to a JSON boolean. Each database operation uses a connection context that commits successful work and closes the connection.

## API Endpoints

| Method | Route | Behavior |
|---|---|---|
| `GET` | `/` | Serves `static/index.html`. |
| `GET` | `/api/books` | Returns books ordered by title, case-insensitively. |
| `POST` | `/api/books` | Validates and inserts a book; returns the new book with HTTP 201. A blank title is rejected. |
| `PATCH` | `/api/books/{book_id}/availability` | Sets the book's availability; returns HTTP 404 when the ID does not exist. |

## Frontend Behavior

- On page load, `loadBooks()` retrieves the collection.
- `renderBooks()` updates the collection display and filters title, author, and ISBN using the search text.
- Form submission posts a new book, then updates the local collection and clears the form.
- Availability controls send the inverse of the current `is_available` value and update the local collection with the response.
- Failed requests are shown in the page's status areas.

## Testing and CI

- `LIBRARY_DB_PATH` overrides the default `library.db` location; `get_database_path()` reads it on every connection, so tests can point each test at a temporary database.
- `tests/conftest.py` provides a `client` fixture (FastAPI `TestClient`) backed by a fresh temporary SQLite file per test.
- `tests/test_api_contract.py` pins the behavior in the endpoint table above: status codes, response shape, trimming, validation limits, title ordering, and the availability 404/422 cases.
- `.github/workflows/ci.yml` installs `requirements-dev.txt` and runs `python -m pytest -q` on every push and pull request.
