"""
Thread-safe in-memory storage layer.

All data lives in plain Python dictionaries keyed by ``str(uuid4())``.
A ``threading.Lock`` protects each store to ensure safe concurrent access
under Uvicorn's thread-pool executor.

Security note: Storage is intentionally **not** persisted.  Restarting
the process clears all data, which is appropriate for this demo but
would need to be replaced with a durable, encrypted datastore in
production.
"""

from __future__ import annotations

import threading
from typing import Any


class MemoryStore:
    """
    Generic in-memory key-value store with coarse-grained locking.

    Each ``MemoryStore`` instance is independent, so collections and
    quotes maintain separate lock scopes.
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock: threading.Lock = threading.Lock()

    def save(self, key: str, value: dict[str, Any]) -> None:
        """Persist *value* under *key*, overwriting any previous entry."""
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> dict[str, Any] | None:
        """Return the record for *key*, or ``None`` if absent."""
        with self._lock:
            return self._data.get(key)

    def exists(self, key: str) -> bool:
        """Return ``True`` if *key* is present."""
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> bool:
        """Remove *key* and return ``True`` if it existed."""
        with self._lock:
            return self._data.pop(key, None) is not None


# ---------------------------------------------------------------------------
# Singleton stores — injected via FastAPI Depends()
# ---------------------------------------------------------------------------
collection_store: MemoryStore = MemoryStore()
quote_store: MemoryStore = MemoryStore()
transfer_store: MemoryStore = MemoryStore()


def get_collection_store() -> MemoryStore:
    """Dependency provider for the collection store."""
    return collection_store


def get_quote_store() -> MemoryStore:
    """Dependency provider for the quote store."""
    return quote_store


def get_transfer_store() -> MemoryStore:
    """Dependency provider for the transfer store."""
    return transfer_store
