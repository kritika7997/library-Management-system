from pathlib import Path
from contextlib import contextmanager
import sqlite3
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "library.db"

app = FastAPI(title="Little Library")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=200)
    isbn: str = Field(default="", max_length=32)


class AvailabilityUpdate(BaseModel):
    is_available: bool


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    connection = connect_database()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                isbn TEXT NOT NULL DEFAULT '',
                is_available INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def serialize_book(row: sqlite3.Row) -> dict:
    book = dict(row)
    book["is_available"] = bool(book["is_available"])
    return book


initialize_database()


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/books")
def list_books() -> list[dict]:
    with database_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, author, isbn, is_available FROM books ORDER BY title COLLATE NOCASE"
        ).fetchall()
    return [serialize_book(row) for row in rows]


@app.post("/api/books", status_code=201)
def add_book(book: BookCreate) -> dict:
    title = book.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be blank")

    with database_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
            (title, book.author.strip(), book.isbn.strip()),
        )
        row = connection.execute(
            "SELECT id, title, author, isbn, is_available FROM books WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_book(row)


@app.patch("/api/books/{book_id}/availability")
def update_availability(book_id: int, update: AvailabilityUpdate) -> dict:
    with database_connection() as connection:
        cursor = connection.execute(
            "UPDATE books SET is_available = ? WHERE id = ?",
            (int(update.is_available), book_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
        row = connection.execute(
            "SELECT id, title, author, isbn, is_available FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
    return serialize_book(row)
