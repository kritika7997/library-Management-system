"""Shared fixtures: isolate the SQLite database used by the API under test."""
import os
import tempfile
from pathlib import Path

# DATABASE_PATH must be set before `main` is imported, because main reads it at import time.
_TEST_DB_DIR = tempfile.TemporaryDirectory(prefix="library-tests-")
os.environ["DATABASE_PATH"] = str(Path(_TEST_DB_DIR.name) / "test_library.db")

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client():
    """Provide a TestClient backed by an empty books table."""
    main.initialize_database()
    with main.database_connection() as connection:
        connection.execute("DELETE FROM books")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'books'")
    with TestClient(main.app) as test_client:
        yield test_client


def pytest_sessionfinish(session, exitstatus):
    _TEST_DB_DIR.cleanup()
