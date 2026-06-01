"""
Shared test fixtures.

The ``client`` fixture resets all in-memory stores before each test to
ensure full isolation.

Security note: Resetting stores between tests prevents data leakage
across test cases, which mirrors the isolation guarantees expected in
production with per-request database transactions.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.memory import collection_store, quote_store, transfer_store


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """
    Yield a ``TestClient`` with clean storage for each test.

    Stores are wiped via internal ``_data.clear()`` rather than
    reinstantiating so that the FastAPI dependency overrides remain
    bound to the same object references.
    """
    # Reset all stores
    collection_store._data.clear()
    quote_store._data.clear()
    transfer_store._data.clear()

    with TestClient(app) as c:
        yield c
