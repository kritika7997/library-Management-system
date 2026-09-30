import os
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a FastAPI TestClient backed by an isolated temporary SQLite DB."""

    db_path = tmp_path / "test-library.db"
    monkeypatch.setenv("LIBRARY_DATABASE_PATH", str(db_path))

    # Reload module so DATABASE_PATH is picked up from env var.
    import main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def test_get_books_empty(client: TestClient) -> None:
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_post_book_creates_and_trims_and_returns_201(client: TestClient) -> None:
    payload = {"title": "  The Hobbit  ", "author": "  Tolkien ", "isbn": "  123  "}

    response = client.post("/api/books", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["title"] == "The Hobbit"
    assert data["author"] == "Tolkien"
    assert data["isbn"] == "123"
    assert data["is_available"] is True


def test_post_blank_title_returns_422(client: TestClient) -> None:
    response = client.post("/api/books", json={"title": "   ", "author": "A", "isbn": ""})
    assert response.status_code == 422


def test_list_books_sorted_case_insensitive_by_title(client: TestClient) -> None:
    client.post("/api/books", json={"title": "banana"})
    client.post("/api/books", json={"title": "Apple"})
    client.post("/api/books", json={"title": "cherry"})

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [book["title"] for book in response.json()]
    assert titles == ["Apple", "banana", "cherry"]


def test_patch_availability_toggles_and_returns_boolean(client: TestClient) -> None:
    create = client.post("/api/books", json={"title": "Dune"})
    book_id = create.json()["id"]

    patch = client.patch(f"/api/books/{book_id}/availability", json={"is_available": False})
    assert patch.status_code == 200
    assert patch.json()["is_available"] is False

    # Confirm persisted
    books = client.get("/api/books").json()
    dune = next(book for book in books if book["id"] == book_id)
    assert dune["is_available"] is False


def test_patch_unknown_id_returns_404(client: TestClient) -> None:
    response = client.patch("/api/books/999999/availability", json={"is_available": False})
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"
