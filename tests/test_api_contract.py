import pytest

"""Contract tests pinning the API behavior documented in HLD.md / LLD.md."""
BOOK_KEYS = {"id", "title", "author", "isbn", "is_available"}


def add(client, **payload):
    return client.post("/api/books", json=payload)


def test_home_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_list_is_empty_initially(client):
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_create_returns_201_with_defaults(client):
    response = add(client, title="  Dune  ")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == BOOK_KEYS
    assert body["title"] == "Dune"
    assert body["author"] == ""
    assert body["isbn"] == ""
    assert body["is_available"] is True


def test_create_trims_and_stores_all_fields(client):
    body = add(client, title="Emma", author=" Austen ", isbn=" 123 ").json()
    assert (body["author"], body["isbn"]) == ("Austen", "123")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "ok", "author": "x" * 201},
        {"title": "ok", "isbn": "x" * 33},
    ],
)
def test_create_rejects_invalid_payload(client, payload):
    assert add(client, **payload).status_code == 422
    assert client.get("/api/books").json() == []


def test_list_ordered_by_title_case_insensitive(client):
    for title in ["banana", "Cherry", "apple"]:
        add(client, title=title)
    titles = [book["title"] for book in client.get("/api/books").json()]
    assert titles == ["apple", "banana", "Cherry"]


def test_availability_toggle_persists(client):
    book_id = add(client, title="Dune").json()["id"]
    response = client.patch(f"/api/books/{book_id}/availability", json={"is_available": False})
    assert response.status_code == 200
    assert response.json()["is_available"] is False
    assert client.get("/api/books").json()[0]["is_available"] is False


def test_availability_unknown_book_returns_404(client):
    response = client.patch("/api/books/9999/availability", json={"is_available": False})
    assert response.status_code == 404


def test_availability_requires_boolean(client):
    book_id = add(client, title="Dune").json()["id"]
    response = client.patch(f"/api/books/{book_id}/availability", json={})
    assert response.status_code == 422
