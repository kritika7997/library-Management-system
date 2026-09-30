import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """Create a TestClient backed by a temporary SQLite database."""
    db_path = tmp_path / "test_library.db"

    # Ensure the app uses the temp db before importing main/app.
    os.environ["LITTLE_LIBRARY_DB_PATH"] = str(db_path)

    # Import after setting env var so startup initializes the correct DB.
    from main import app  # noqa: WPS433

    with TestClient(app) as test_client:
        yield test_client


def _create_book(client: TestClient, title: str, author: str = "", isbn: str = "") -> dict:
    response = client.post(
        "/api/books",
        json={
            "title": title,
            "author": author,
            "isbn": isbn,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_books_empty_on_fresh_db(client: TestClient) -> None:
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_post_book_persists_and_trims_title(client: TestClient) -> None:
    created = _create_book(client, title="  The Hobbit  ", author="  Tolkien ", isbn=" 123 ")

    assert created["id"]
    assert created["title"] == "The Hobbit"
    assert created["author"] == "Tolkien"
    assert created["isbn"] == "123"
    assert created["is_available"] is True

    response = client.get("/api/books")
    assert response.status_code == 200

    books = response.json()
    assert len(books) == 1
    assert books[0]["title"] == "The Hobbit"


def test_post_book_rejects_blank_or_whitespace_title(client: TestClient) -> None:
    response = client.post(
        "/api/books",
        json={
            "title": "   ",
            "author": "Someone",
            "isbn": "",
        },
    )

    # Implementation uses HTTPException(422) for blank title.
    assert response.status_code in {400, 422}


def test_get_books_ordered_case_insensitively(client: TestClient) -> None:
    _create_book(client, title="Beta")
    _create_book(client, title="alpha")

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [book["title"] for book in response.json()]
    assert titles == ["alpha", "Beta"]


def test_patch_availability_404_for_missing_book(client: TestClient) -> None:
    response = client.patch("/api/books/999/availability", json={"is_available": False})
    assert response.status_code == 404


def test_patch_availability_updates_and_returns_boolean(client: TestClient) -> None:
    created = _create_book(client, title="Dune")

    response = client.patch(
        f"/api/books/{created['id']}/availability",
        json={"is_available": False},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["is_available"] is False
    assert isinstance(payload["is_available"], bool)

    response2 = client.patch(
        f"/api/books/{created['id']}/availability",
        json={"is_available": True},
    )
    assert response2.status_code == 200
    assert response2.json()["is_available"] is True
