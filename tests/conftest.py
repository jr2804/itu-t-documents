"""Pytest configuration and fixtures for ITU-T Document Downloader."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fakes import FakeClient

_test_dir = Path(__file__).parent


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Return the path to the test data directory."""
    return _test_dir / "data"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the path to the directory holding the recorded HTML fixtures."""
    return _test_dir / "fixtures"


@pytest.fixture(scope="session")
def cache_subdir(request: pytest.FixtureRequest, subdir: str) -> Path:
    """Return a subdirectory in the pytest cache directory.

    Can be used by other fixtures to easily get a cache directory.
    """
    return Path(request.config.cache.mkdir(subdir))


@pytest.fixture
def fake_client(fixtures_dir: Path) -> FakeClient:
    """Return a client that serves the recorded fixtures."""
    return FakeClient(fixtures_dir)
