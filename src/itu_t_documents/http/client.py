"""HTTP access to the ITU-T document management system.

Two HTTP clients are used: a **cached** client for the public meeting document
pages, backed by :mod:`hishel`, so that repeated metadata queries are answered
from the local SQLite cache without authentication again; and a **session**
client that keeps the TIES cookies for the handshake and the downloads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import httpx
from hishel import SqliteStorage
from hishel.httpx import CacheClient

from itu_t_documents.auth.ties import SESSION_PROBE_URL, AuthenticationError, TiesAuthenticator
from itu_t_documents.config.settings import Settings

#: Name of the SQLite file holding the raw HTTP cache.
HTTP_CACHE_FILE = "http-cache.sqlite"

#: Default lifetime of a cached HTTP response in seconds.
HTTP_CACHE_TTL = 60 * 60 * 24

#: Number of documents the ITU-T document pages show per page. The value is
#: stored in a cookie by the web interface, whose page size control goes up
#: to 900. A longer listing spans several pages, all of which are read.
PAGE_SIZE = 900

#: Charset used by the ITU-T meeting document pages. Those pages are encoded
#: in ISO-8859-1 but do not declare it in their content type header.
DEFAULT_CHARSET = "iso-8859-1"


class ItuClient(Protocol):
    """The HTTP access that the API needs.

    The production implementation is :class:`ItuHttpClient`; tests use a
    stand-in that serves recorded pages.
    """

    def get_text(self, url: str) -> str:
        """Return the decoded body of a page."""
        ...

    def authenticate(self, target: str | None = None) -> httpx.Client:
        """Log in and return the authenticated client.

        Args:
            target: The protected resource the session is opened for.

        Returns:
            The client that carries the session.
        """
        ...

    def close(self) -> None:
        """Close the client."""
        ...


class ItuHttpClient:
    """Access to ``www.itu.int`` with response caching and TIES authentication."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Create the client.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
        """
        self.settings = settings or Settings()
        self._cache_dir = self.settings.resolved_cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        limits = httpx.Limits(max_connections=self.settings.max_concurrency, max_keepalive_connections=self.settings.max_concurrency)
        self._cached_client: httpx.Client = CacheClient(
            storage=SqliteStorage(
                database_path=str(self._cache_dir / HTTP_CACHE_FILE),
                default_ttl=HTTP_CACHE_TTL,
            ),
            timeout=self.settings.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.verify_tls,
            limits=limits,
        )
        self._session_client = httpx.Client(
            timeout=self.settings.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.verify_tls,
            limits=limits,
        )
        for client in (self._cached_client, self._session_client):
            client.cookies.set("ITUDMS_PageSize", str(PAGE_SIZE), domain="www.itu.int")
        self._authenticator: TiesAuthenticator | None = None

    @property
    def cached_client(self) -> httpx.Client:
        """The caching client used for public meeting document pages."""
        return self._cached_client

    @property
    def session_client(self) -> httpx.Client:
        """The client that keeps the TIES session cookies."""
        return self._session_client

    def get(self, url: str) -> httpx.Response:
        """Fetch a public page through the HTTP cache.

        Args:
            url: The absolute URL to fetch.

        Returns:
            The response; the status code has to be checked by the caller.
        """
        return self._cached_client.get(url)

    def get_text(self, url: str) -> str:
        """Fetch a public page through the HTTP cache and return its body.

        Args:
            url: The absolute URL to fetch.

        Returns:
            The decoded response body.
        """
        response = self.get(url)
        response.raise_for_status()
        return decode(response)

    def authenticate(self, target: str | None = None) -> httpx.Client:
        """Log in to the DMS and return the authenticated client.

        Args:
            target: The protected resource the session is opened for. The
                access policy only opens a session for a protected resource, so
                the default points at a document file that does not exist.

        Returns:
            The session client carrying a valid TIES session.

        Raises:
            AuthenticationError: When no credentials are configured or the
                identity provider rejects them.
        """
        if not self.settings.has_credentials():
            raise AuthenticationError(self.settings.credentials_message)
        if self._authenticator is None:
            self._authenticator = TiesAuthenticator(
                self._session_client,
                self.settings.ties_username or "",
                self.settings.ties_password.get_secret_value() if self.settings.ties_password else "",
            )
        if not self._authenticator.is_authenticated:
            self._authenticator.login_for(target or SESSION_PROBE_URL)
        return self._session_client

    def close(self) -> None:
        """Close both underlying HTTP clients."""
        self._cached_client.close()
        self._session_client.close()

    def __enter__(self) -> ItuHttpClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def decode(response: httpx.Response) -> str:
    """Decode the body of a response.

    Args:
        response: The response to decode.

    Returns:
        The decoded text of the response.
    """
    charset = response.charset_encoding or DEFAULT_CHARSET
    return response.content.decode(charset, errors="replace")


def cache_file(settings: Settings) -> Path:
    """Return the path of the raw HTTP cache file.

    Args:
        settings: The configuration to use.

    Returns:
        The path of the SQLite cache file.
    """
    return settings.resolved_cache_dir / HTTP_CACHE_FILE
