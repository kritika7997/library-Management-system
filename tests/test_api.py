import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    """Create a TestClient backed by an isolated temporary SQLite database."""
    import main

    # Point the app at a temp DB file and ensure schema exists.
    main.DATABASE_PATH = tmp_path / "test_library.db"
    main.initialize_database()

    # Ensure we start from a clean state each test.
    with main.database_connection() as connection:
        connection.execute("DELETE FROM books")

    return TestClient(main.app)


def _create_book(client: TestClient, title: str, author: str = "", isbn: str = "") -> dict:
    response = client.post(
        "/api/books",
        json={"title": title, "author": author, "isbn": isbn},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_books_returns_200_and_sorted_case_insensitively(client: TestClient):
    _create_book(client, "banana")
    _create_book(client, "Apple")
    _create_book(client, "cherry")

    response = client.get("/api/books")
    assert response.status_code == 200

    books = response.json()
    assert isinstance(books, list)
    titles = [book["title"] for book in books]

    # Ensure titles are sorted case-insensitively.
    assert titles == sorted(titles, key=str.casefold)


def test_post_books_returns_201_and_trims_fields(client: TestClient):
    response = client.post(
        "/api/books",
        json={"title": "  The Hobbit  ", "author": "  Tolkien ", "isbn": "  978-0  "},
    )

    assert response.status_code == 201
    payload = response.json()

    assert payload["title"] == "The Hobbit"
    assert payload["author"] == "Tolkien"
    assert payload["isbn"] == "978-0"
    assert payload["is_available"] is True
    assert isinstance(payload["id"], int)


def test_post_books_rejects_blank_title_with_422(client: TestClient):
    response = client.post(
        "/api/books",
        json={"title": "   ", "author": "Someone", "isbn": ""},
    )

    assert response.status_code == 422


def test_patch_availability_updates_and_missing_returns_404(client: TestClient):
    created = _create_book(client, "Dune")

    patch_response = client.patch(
        f"/api/books/{created['id']}/availability",
        json={"is_available": False},
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["id"] == created["id"]
    assert updated["is_available"] is False

    missing_response = client.patch(
        "/api/books/999999/availability",
        json={"is_available": False},
    )
    assert missing_response.status_code == 404
