import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a TestClient with an isolated SQLite DB.

    The application reads LIBRARY_DB_PATH at import time, so we set it before importing main.
    """

    db_path = tmp_path / "test-library.db"
    monkeypatch.setenv("LIBRARY_DB_PATH", str(db_path))

    # Ensure a clean import for each test so DATABASE_PATH picks up our env var.
    import main  # noqa: WPS433

    return TestClient(main.app)


def test_get_books_empty_list_on_fresh_db(client: TestClient) -> None:
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_get_books_ordered_case_insensitively(client: TestClient) -> None:
    # Insert out of order, ensure API sorts by title COLLATE NOCASE
    client.post("/api/books", json={"title": "Banana", "author": "", "isbn": ""})
    client.post("/api/books", json={"title": "apple", "author": "", "isbn": ""})

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [book["title"] for book in response.json()]
    assert titles == ["apple", "Banana"]


def test_post_books_returns_201_and_boolean_is_available(client: TestClient) -> None:
    response = client.post(
        "/api/books",
        json={"title": "  Dune  ", "author": "  Frank Herbert ", "isbn": "  9780441013593  "},
    )
    assert response.status_code == 201

    payload = response.json()
    assert payload["title"] == "Dune"
    assert payload["author"] == "Frank Herbert"
    assert payload["isbn"] == "9780441013593"
    assert isinstance(payload["is_available"], bool)
    assert payload["is_available"] is True


def test_post_books_rejects_blank_title_with_422(client: TestClient) -> None:
    response = client.post("/api/books", json={"title": "   ", "author": "", "isbn": ""})
    assert response.status_code == 422


def test_patch_availability_updates_and_returns_boolean(client: TestClient) -> None:
    created = client.post("/api/books", json={"title": "Dune", "author": "", "isbn": ""}).json()

    response = client.patch(
        f"/api/books/{created['id']}/availability",
        json={"is_available": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert isinstance(payload["is_available"], bool)
    assert payload["is_available"] is False


def test_patch_availability_returns_404_for_missing_book_id(client: TestClient) -> None:
    response = client.patch("/api/books/999999/availability", json={"is_available": False})
    assert response.status_code == 404
