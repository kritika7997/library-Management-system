import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient backed by a fresh, isolated SQLite database per test."""
    monkeypatch.setenv("LIBRARY_DB_PATH", str(tmp_path / "test_library.db"))
    main.initialize_database()
    with TestClient(main.app) as test_client:
        yield test_client
