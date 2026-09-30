import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a TestClient with an isolated temporary SQLite DB.

    The app module initializes the DB on import, so we must set LIBRARY_DB_PATH
    *before* importing main.
    """

    db_path = tmp_path / "test_library.db"
    monkeypatch.setenv("LIBRARY_DB_PATH", str(db_path))

    # Import after env var is set so initialization uses the test DB.
    import main  # noqa: WPS433

    return TestClient(main.app)


def test_get_books_returns_array(client: TestClient) -> None:
    response = client.get("/api/books")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_post_book_creates_and_persists(client: TestClient) -> None:
    payload = {"title": "  The Hobbit  ", "author": " J.R.R. Tolkien ", "isbn": " 9780547928227 "}
    response = client.post("/api/books", json=payload)

    assert response.status_code == 201
    created = response.json()
    assert created["id"] > 0
    assert created["title"] == "The Hobbit"
    assert created["author"] == "J.R.R. Tolkien"
    assert created["isbn"] == "9780547928227"
    assert created["is_available"] is True

    list_response = client.get("/api/books")
    assert list_response.status_code == 200
    books = list_response.json()
    assert any(book["id"] == created["id"] for book in books)


def test_post_book_blank_title_returns_422(client: TestClient) -> None:
    response = client.post("/api/books", json={"title": "   "})
    assert response.status_code == 422


def test_patch_availability_updates_and_returns_book(client: TestClient) -> None:
    create_response = client.post("/api/books", json={"title": "Dune"})
    book_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/books/{book_id}/availability",
        json={"is_available": False},
    )

    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["id"] == book_id
    assert updated["is_available"] is False


def test_patch_availability_missing_book_returns_404(client: TestClient) -> None:
    response = client.patch("/api/books/999999/availability", json={"is_available": False})
    assert response.status_code == 404
