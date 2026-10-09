# Little Library

A small library-management starter built with plain HTML, CSS, and JavaScript, FastAPI, and SQLite. The frontend is intentionally an MVP, not a finished library system.

## Run locally on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000. The SQLite database (`library.db`) is created beside `main.py` when the app starts. API documentation is available at http://127.0.0.1:8000/docs.

## Included

- Add a book with a title, author, and optional ISBN
- Browse and search the collection
- Mark a book available or checked out
- SQLite persistence

## Not included yet

- Member accounts, loans, due dates, or fines
- Editing or removing books
- Authentication, authorization, or automated tests
- A production-ready frontend or deployment setup 
