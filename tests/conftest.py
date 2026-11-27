"""Pytest configuration and fixtures for ITU-T Documents."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy.pool import QueuePool

from itu_t_documents.config.settings import Settings
from itu_t_documents.storage.database import MetadataStore
from tests.fakes import FakeClient

_test_dir = Path(__file__).parent


@pytest.fixture(autouse=True)
def close_stores(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Close every metadata store a test opened once the test ends.

    The tests open stores as they need them. Closing them here keeps the
    SQLite connections from outliving the test that opened them.
    """
    stores: list[MetadataStore] = []
    initialise = MetadataStore.__init__

    def opening(self: MetadataStore, settings: Settings | None = None) -> None:
        initialise(self, settings)
        stores.append(self)

    monkeypatch.setattr(MetadataStore, "__init__", opening)
    yield
    for store in stores:
        store.close()


@pytest.fixture
def pooled_connections() -> Callable[[MetadataStore], int]:
    """Return a function that counts the connections a store keeps in its pool."""

    def count(store: MetadataStore) -> int:
        pool = store.engine.pool
        assert isinstance(pool, QueuePool)
        return pool.checkedin()

    return count


@pytest.fixture
def fake_client(fixtures_dir: Path) -> FakeClient:
    """Return a client that serves the recorded fixtures."""
    return FakeClient(fixtures_dir)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the path to the directory holding the recorded HTML fixtures."""
    return _test_dir / "fixtures"
