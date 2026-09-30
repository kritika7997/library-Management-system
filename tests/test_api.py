import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a TestClient wired to a temporary SQLite database.

    IMPORTANT: main.py initializes the database at import time, so we must set
    DATABASE_PATH before importing/reloading the module.
    """

    db_path = tmp_path / "test_library.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Ensure a clean import using the env var.
    import main

    importlib.reload(main)

    return TestClient(main.app)


def test_get_books_sorted_case_insensitive(client: TestClient) -> None:
    # Create books with varying case to validate ORDER BY ... COLLATE NOCASE.
    client.post("/api/books", json={"title": "banana", "author": "", "isbn": ""})
    client.post("/api/books", json={"title": "Apple", "author": "", "isbn": ""})
    client.post("/api/books", json={"title": "cherry", "author": "", "isbn": ""})

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [item["title"] for item in response.json()]
    assert titles == ["Apple", "banana", "cherry"]


def test_post_book_creates_and_is_retrievable(client: TestClient) -> None:
    response = client.post(
        "/api/books",
        json={"title": "The Hobbit", "author": "J.R.R. Tolkien", "isbn": ""},
    )
    assert response.status_code == 201

    created = response.json()
    assert created["id"]
    assert created["title"] == "The Hobbit"
    assert created["author"] == "J.R.R. Tolkien"
    assert created["is_available"] is True

    list_response = client.get("/api/books")
    assert list_response.status_code == 200

    all_books = list_response.json()
    assert any(book["id"] == created["id"] for book in all_books)


def test_post_book_rejects_blank_title(client: TestClient) -> None:
    response = client.post(
        "/api/books",
        json={"title": "   ", "author": "Someone", "isbn": ""},
    )
    assert response.status_code == 422


def test_patch_availability_updates_and_returns_boolean(client: TestClient) -> None:
    create = client.post(
        "/api/books",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": ""},
    )
    book_id = create.json()["id"]

    patch = client.patch(f"/api/books/{book_id}/availability", json={"is_available": False})
    assert patch.status_code == 200

    payload = patch.json()
    assert payload["id"] == book_id
    assert payload["is_available"] is False
    assert isinstance(payload["is_available"], bool)


def test_patch_availability_non_existent_returns_404(client: TestClient) -> None:
    response = client.patch("/api/books/999999/availability", json={"is_available": False})
    assert response.status_code == 404
