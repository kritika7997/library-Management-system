"""API tests for the Little Library service."""
import main


def create_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "isbn": "123"}
    payload.update(overrides)
    return client.post("/api/books", json=payload)


def test_uses_isolated_database():
    assert "library-tests-" in str(main.DATABASE_PATH)


def test_list_books_empty(client):
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []


def test_add_book_returns_created_book(client):
    response = create_book(client)
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "title": "Dune",
        "author": "Frank Herbert",
        "isbn": "123",
        "is_available": True,
    }


def test_add_book_trims_whitespace(client):
    body = create_book(client, title="  Emma  ", author=" Austen ", isbn=" 9 ").json()
    assert (body["title"], body["author"], body["isbn"]) == ("Emma", "Austen", "9")


def test_add_book_optional_fields_default_to_empty(client):
    response = client.post("/api/books", json={"title": "Solo"})
    assert response.status_code == 201
    assert response.json()["author"] == ""
    assert response.json()["isbn"] == ""


def test_add_book_rejects_missing_title(client):
    assert client.post("/api/books", json={"author": "x"}).status_code == 422


def test_add_book_rejects_empty_title(client):
    assert create_book(client, title="").status_code == 422


def test_add_book_rejects_blank_title(client):
    response = create_book(client, title="   ")
    assert response.status_code == 422
    assert response.json()["detail"] == "Title cannot be blank"


def test_add_book_rejects_overlong_title(client):
    assert create_book(client, title="a" * 201).status_code == 422


def test_list_books_sorted_by_title_case_insensitive(client):
    for title in ["banana", "Cherry", "apple"]:
        create_book(client, title=title)
    titles = [book["title"] for book in client.get("/api/books").json()]
    assert titles == ["apple", "banana", "Cherry"]


def test_update_availability_toggles_book(client):
    book_id = create_book(client).json()["id"]
    response = client.patch(f"/api/books/{book_id}/availability", json={"is_available": False})
    assert response.status_code == 200
    assert response.json()["is_available"] is False
    assert client.get("/api/books").json()[0]["is_available"] is False


def test_update_availability_unknown_book_returns_404(client):
    response = client.patch("/api/books/999/availability", json={"is_available": True})
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_update_availability_rejects_invalid_payload(client):
    book_id = create_book(client).json()["id"]
    response = client.patch(f"/api/books/{book_id}/availability", json={"is_available": "maybe"})
    assert response.status_code == 422


def test_home_serves_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
