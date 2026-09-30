import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path):
    """Create a TestClient using an isolated SQLite database per test."""
    db_path = tmp_path / "test-library.db"

    # Ensure main.py picks up the test database location.
    os.environ["DATABASE_PATH"] = str(db_path)

    # Import after setting env var so get_database_path() uses it.
    import importlib
    import main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def test_get_books_returns_empty_array_for_fresh_db(client: TestClient):
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_get_books_are_ordered_case_insensitively_by_title(client: TestClient):
    # Insert titles that would differ under case-sensitive ordering.
    client.post(
        "/api/books",
        json={"title": "banana", "author": "a", "isbn": "1"},
    )
    client.post(
        "/api/books",
        json={"title": "Apple", "author": "b", "isbn": "2"},
    )
    client.post(
        "/api/books",
        json={"title": "cherry", "author": "c", "isbn": "3"},
    )

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [book["title"] for book in response.json()]
    assert titles == ["Apple", "banana", "cherry"]


def test_post_books_returns_201_and_trims_fields(client: TestClient):
    response = client.post(
        "/api/books",
        json={"title": "  The Hobbit  ", "author": "  Tolkien ", "isbn": "  978  "},
    )
    assert response.status_code == 201

    payload = response.json()
    assert payload["id"] > 0
    assert payload["title"] == "The Hobbit"
    assert payload["author"] == "Tolkien"
    assert payload["isbn"] == "978"
    assert payload["is_available"] is True


def test_post_books_rejects_blank_or_whitespace_title_with_422(client: TestClient):
    # min_length=1 passes for whitespace; app-level strip check should reject.
    response = client.post(
        "/api/books",
        json={"title": "   ", "author": "a", "isbn": "1"},
    )
    assert response.status_code == 422


def test_patch_availability_toggles_and_404_when_missing(client: TestClient):
    create = client.post(
        "/api/books",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": ""},
    )
    book = create.json()
    assert book["is_available"] is True

    updated = client.patch(
        f"/api/books/{book['id']}/availability",
        json={"is_available": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_available"] is False

    missing = client.patch(
        "/api/books/999999/availability",
        json={"is_available": False},
    )
    assert missing.status_code == 404
