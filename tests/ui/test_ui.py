"""Browser (Playwright) tests for the Little Library frontend.

Skipped automatically when the `playwright` package is not installed.
The app runs as a real uvicorn process against a temporary SQLite file.
"""
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def server():
    port = _free_port()
    with tempfile.TemporaryDirectory(prefix="library-ui-tests-") as tmp:
        db_path = Path(tmp) / "ui_library.db"
        env = {**os.environ, "DATABASE_PATH": str(db_path)}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT,
            env=env,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(base_url + "/api/books", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("uvicorn did not start")
            yield base_url, db_path
        finally:
            proc.terminate()
            proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not os.environ.get("HEADED"),
            slow_mo=int(os.environ.get("SLOW_MO", "0")),
        )
        yield browser
        browser.close()


@pytest.fixture()
def page(server, browser):
    base_url, db_path = server
    connection = sqlite3.connect(db_path)
    with connection:
        connection.execute("DELETE FROM books")
    connection.close()
    page = browser.new_page(base_url=base_url)
    page.goto("/")
    yield page
    page.close()


def add_book(page, title, author="", isbn=""):
    page.fill("#title", title)
    page.fill("#author", author)
    page.fill("#isbn", isbn)
    page.click("button.add-button")


def test_empty_shelf_state(page):
    expect(page.locator("#book-count")).to_have_text("0 books in your collection")
    expect(page.locator(".empty-state")).to_have_text("Your shelf is empty. Add a book to get started.")


def test_add_book_appears_on_shelf_and_form_resets(page):
    add_book(page, "Dune", "Frank Herbert", "123")
    row = page.locator(".book-row")
    expect(row).to_have_count(1)
    expect(row.locator(".book-title")).to_have_text("Dune")
    expect(row.locator(".book-meta")).to_contain_text("Frank Herbert")
    expect(row.locator(".book-meta")).to_contain_text("ISBN 123")
    expect(row.locator(".availability-button")).to_have_text("Available")
    expect(page.locator("#book-count")).to_have_text("1 book in your collection")
    expect(page.locator("#title")).to_have_value("")
    expect(page.locator("#title")).to_be_focused()


def test_added_book_persists_after_reload(page):
    add_book(page, "Persisted")
    expect(page.locator(".book-row")).to_have_count(1)
    page.reload()
    expect(page.locator(".book-title")).to_have_text("Persisted")


def test_title_only_book_has_no_metadata(page):
    add_book(page, "Solo")
    expect(page.locator(".book-row")).to_have_count(1)
    expect(page.locator(".book-meta")).to_have_count(0)


def test_empty_title_blocked_by_browser_validation(page):
    add_book(page, "")
    expect(page.locator(".book-row")).to_have_count(0)
    assert page.eval_on_selector("#title", "el => el.validity.valueMissing") is True


def test_blank_title_shows_server_error(page):
    add_book(page, "   ")
    expect(page.locator("#form-message")).not_to_be_empty()
    expect(page.locator(".book-row")).to_have_count(0)


def test_toggle_availability_and_persist(page):
    add_book(page, "Dune")
    button = page.locator(".availability-button")
    expect(button).to_have_text("Available")
    button.click()
    expect(button).to_have_text("Checked out")
    expect(button).to_have_class("availability-button checked-out")
    page.reload()
    expect(page.locator(".availability-button")).to_have_text("Checked out")
    page.locator(".availability-button").click()
    expect(page.locator(".availability-button")).to_have_text("Available")


def test_books_sorted_by_title(page):
    for title in ["Banana", "Apple"]:
        add_book(page, title)
        expect(page.locator(".book-row")).to_have_count(1 if title == "Banana" else 2)
    expect(page.locator(".book-title")).to_have_text(["Apple", "Banana"])


def test_search_filters_and_shows_no_match_message(page):
    add_book(page, "Dune", "Frank Herbert")
    expect(page.locator(".book-row")).to_have_count(1)
    add_book(page, "Emma", "Jane Austen")
    expect(page.locator(".book-row")).to_have_count(2)
    page.fill("#book-search", "austen")
    expect(page.locator(".book-title")).to_have_text(["Emma"])
    page.fill("#book-search", "zzz")
    expect(page.locator(".empty-state")).to_have_text("No books match that search.")
    page.fill("#book-search", "")
    expect(page.locator(".book-row")).to_have_count(2)


def test_title_is_rendered_as_text_not_html(page):
    add_book(page, "<b>Bold</b>")
    expect(page.locator(".book-title")).to_have_text("<b>Bold</b>")
    expect(page.locator(".book-title b")).to_have_count(0)


def test_toggle_failure_shows_error_message(page):
    add_book(page, "Dune")
    expect(page.locator(".book-row")).to_have_count(1)
    page.route("**/api/books/*/availability", lambda route: route.fulfill(
        status=404, content_type="application/json", body='{"detail": "Book not found"}'))
    page.locator(".availability-button").click()
    expect(page.locator("#form-message")).to_have_text("Book not found")
    expect(page.locator(".availability-button")).to_have_text("Available")


def test_load_failure_shows_error_state(server, browser):
    base_url, _ = server
    page = browser.new_page(base_url=base_url)
    page.route("**/api/books", lambda route: route.fulfill(
        status=500, content_type="application/json", body="{}"))
    page.goto("/")
    expect(page.locator("#book-count")).to_have_text("Could not load collection")
    page.close()
