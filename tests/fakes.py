"""Test doubles that stand in for the ITU-T web site."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import httpx

from itu_doc_downloader.http.client import ItuClient

#: The bytes a fake document download returns.
DOCUMENT_BYTES = b"document-bytes"

#: Pattern of a document identifier in the ``parent`` parameter.
_DOCUMENT_ID_RE = re.compile(r"T\d{2}-SG\d{1,3}(-\d{6})?-(TD|COL|R|C)(-[A-Z0-9]+)?-\d{4}")


class FakeClient(ItuClient):
    """Serves the recorded fixtures instead of contacting the ITU-T web site."""

    def __init__(self, fixtures_dir: Path) -> None:
        """Create the fake client.

        Args:
            fixtures_dir: The directory holding the recorded fixtures.
        """
        self.fixtures_dir = fixtures_dir
        self.requested: list[str] = []
        self.login_targets: list[str] = []
        self.session = httpx.Client(
            transport=httpx.MockTransport(self._document_handler()),
            follow_redirects=True,
        )

    def _document_handler(self) -> Callable[[httpx.Request], httpx.Response]:
        """Return a handler that records the requested URLs."""

        def handler(request: httpx.Request) -> httpx.Response:
            """Return the bytes of a document."""
            self.requested.append(str(request.url))
            return httpx.Response(200, content=DOCUMENT_BYTES)

        return handler

    def get_text(self, url: str) -> str:
        """Return the fixture that matches the requested URL."""
        self.requested.append(url)
        if "loqr.aspx" in url:
            return self._read("questions.html")
        if url.endswith("/md/T25-SG12/en"):
            return self._read("meeting_index.html")
        parent = url.rsplit("parent=", maxsplit=1)[-1]
        if _DOCUMENT_ID_RE.fullmatch(parent):
            return self._read("detail_temporary_document.html")
        if parent.endswith("-C"):
            return self._read("listing_contributions.html")
        if parent.endswith("-TD"):
            return self._read("listing_temporary_documents.html")
        return self._read("detail_temporary_document.html")

    def authenticate(self, target: str | None = None) -> httpx.Client:
        """Return the authenticated session.

        Args:
            target: The protected resource the session is opened for.

        Returns:
            The client that carries the session.
        """
        if target is not None:
            self.login_targets.append(target)
        return self.session

    def close(self) -> None:
        """Close the fake client."""
        self.session.close()

    def _read(self, name: str) -> str:
        """Return the content of a fixture."""
        return (self.fixtures_dir / name).read_text(encoding="utf-8")
