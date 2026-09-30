import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return a TestClient backed by an isolated SQLite DB.

    main.py reads DATABASE_PATH from the environment; we set it before importing
    the module to ensure each test run uses a clean DB.
    """

    db_path = tmp_path / "test-library.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Import after setting env var so module picks up the correct DB location.
    import main

    # Ensure schema exists for the test DB.
    main.initialize_database()

    return TestClient(main.app)


def _add_book(client: TestClient, title: str, author: str = "", isbn: str = "") -> dict:
    response = client.post(
        "/api/books",
        json={"title": title, "author": author, "isbn": isbn},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_books_order_case_insensitive(client: TestClient) -> None:
    _add_book(client, title="Banana")
    _add_book(client, title="apple")

    response = client.get("/api/books")
    assert response.status_code == 200

    titles = [book["title"] for book in response.json()]
    assert titles == ["apple", "Banana"]


def test_post_book_rejects_blank_title(client: TestClient) -> None:
    response = client.post("/api/books", json={"title": "   ", "author": "", "isbn": ""})
    assert response.status_code == 422
    assert response.json()["detail"] == "Title cannot be blank"


def test_post_book_returns_schema_and_default_availability(client: TestClient) -> None:
    created = _add_book(client, title="Dune", author="Frank Herbert", isbn="")

    assert "id" in created
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["isbn"] == ""

    # Contract: is_available serialized as boolean and defaults to True.
    assert isinstance(created["is_available"], bool)
    assert created["is_available"] is True


def test_patch_availability_updates_and_persists(client: TestClient) -> None:
    created = _add_book(client, title="Neuromancer")

    patch = client.patch(
        f"/api/books/{created['id']}/availability",
        json={"is_available": False},
    )
    assert patch.status_code == 200
    assert patch.json()["is_available"] is False

    listed = client.get("/api/books")
    assert listed.status_code == 200

    by_id = {book["id"]: book for book in listed.json()}
    assert by_id[created["id"]]["is_available"] is False


def test_patch_availability_returns_404_when_missing(client: TestClient) -> None:
    response = client.patch("/api/books/999999/availability", json={"is_available": False})
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"
