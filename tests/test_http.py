"""Tests for the HTTP access to the ITU-T document management system."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from itu_t_documents.auth.ties import AuthenticationError
from itu_t_documents.config.settings import Settings
from itu_t_documents.http.client import PAGE_SIZE, ItuHttpClient, cache_file, decode


def _client(tmp_path: Path, handler) -> ItuHttpClient:
    """Return an HTTP client wired to a mock transport."""
    settings = Settings(cache_dir=tmp_path)
    client = ItuHttpClient(settings)
    client._cached_client = httpx.Client(  # noqa: SLF001
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
        headers={"User-Agent": settings.user_agent},
    )
    return client


def test_get_text_uses_the_cached_client(tmp_path: Path) -> None:
    """A page is fetched through the caching client."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text="<html>listing</html>", headers={"content-type": "text/html; charset=utf-8"})

    with _client(tmp_path, handler) as client:
        body = client.get_text("https://www.itu.int/md/T25-SG12/en")

    assert body == "<html>listing</html>"
    assert requested == ["https://www.itu.int/md/T25-SG12/en"]


def test_page_size_cookie_is_set(tmp_path: Path) -> None:
    """The page size cookie is set on both clients."""
    with ItuHttpClient(Settings(cache_dir=tmp_path)) as client:
        assert client.cached_client.cookies.get("ITUDMS_PageSize", domain="www.itu.int") == str(PAGE_SIZE)
        assert client.session_client.cookies.get("ITUDMS_PageSize", domain="www.itu.int") == str(PAGE_SIZE)


def test_decode_uses_the_declared_charset() -> None:
    """A declared charset wins."""
    response = httpx.Response(200, content="café".encode(), headers={"content-type": "text/html; charset=utf-8"})

    assert decode(response) == "café"


def test_decode_falls_back_to_the_default_charset() -> None:
    """A page without a charset is decoded as ISO-8859-1."""
    response = httpx.Response(200, content="café".encode("iso-8859-1"), headers={"content-type": "text/html"})

    assert decode(response) == "café"


def test_authenticate_without_credentials(tmp_path: Path) -> None:
    """A login without credentials is refused."""
    with ItuHttpClient(Settings(cache_dir=tmp_path)) as client, pytest.raises(AuthenticationError, match="no TIES credentials"):
        client.authenticate()


def test_cache_file_path(tmp_path: Path) -> None:
    """The raw HTTP cache lives in the cache directory."""
    settings = Settings(cache_dir=tmp_path)

    assert cache_file(settings) == tmp_path / "http-cache.sqlite"
