"""Test doubles that stand in for the ITU-T web site."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import httpx

from itu_t_documents.http.client import ItuClient

#: The bytes a fake document download returns.
DOCUMENT_BYTES = b"document-bytes"

#: The page the access policy answers for a document outside the membership.
DENIED_PAGE = b"<html><body><h2>401 - Unauthorized: Access is denied due to invalid credentials.</h2></body></html>"

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
        self.denied = False
        self.missing = False
        self.session = httpx.Client(
            transport=httpx.MockTransport(self._document_handler()),
            follow_redirects=True,
        )

    def _document_handler(self) -> Callable[[httpx.Request], httpx.Response]:
        """Return a handler that records the requested URLs."""

        def handler(request: httpx.Request) -> httpx.Response:
            """Return the bytes of a document."""
            self.requested.append(str(request.url))
            if self.denied:
                return httpx.Response(401, content=DENIED_PAGE, headers={"content-type": "text/html"})
            if self.missing:
                return httpx.Response(404, content=b"not found")
            return httpx.Response(200, content=DOCUMENT_BYTES)

        return handler

    def get_text(self, url: str) -> str:
        """Return the fixture that matches the requested URL."""
        self.requested.append(url)
        if "loqr.aspx" in url:
            return self._read("questions.html")
        if "sgstructure.aspx" in url:
            group = re.search(r"Group=(\d+)", url)
            number = group.group(1) if group else "0"
            if number == "12":
                return self._read("study_group_structure.html")
            if number == "13":
                return self._read("study_group_structure_13.html")
            return self._structure_of(number)
        if "/studygroups/" in url and url.endswith("/Pages/default.aspx"):
            return self._read("study_groups_index.html")
        if url.endswith("/md/T25-SG12/en"):
            return self._read("meeting_index.html")
        parent = url.rsplit("parent=", maxsplit=1)[-1]
        if parent == "T25-SG02-C-0001":
            return self._read("detail_revised_contribution.html")
        if parent == "T25-SG02-C-0002":
            return self._read("detail_revision_only.html")
        if parent == "T25-SG12-250114-TD":
            return self._listing("listing_contributions.html")
        if parent == "T25-SG12-270119-C":
            return self._read("listing_contributions.html")
        if _DOCUMENT_ID_RE.fullmatch(parent):
            return self._read("detail_temporary_document.html")
        if parent.endswith("-C"):
            return self._listing("listing_contributions.html")
        if parent == "T25-SG12-261015-TD-GEN":
            return self._listing("listing_temporary_documents_subtype.html")
        if parent.endswith("-TD") or "-TD-" in parent:
            return self._listing("listing_temporary_documents.html")
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

    def _structure_of(self, number: str) -> str:
        """Return the structure page of a study group without a recording.

        Only the plenary and a single question are held, so that a question
        number can be told apart from the one of another study group.

        Args:
            number: The number of the study group.

        Returns:
            The HTML of a structure page.
        """
        return f"""<html><body><table>
<tr><td>PLEN</td><td></td></tr>
<tr><td>Q1/{number}</td><td>A question of study group {number}</td></tr>
<tr><td>WP1/{number}</td><td>A working group of study group {number}</td></tr>
</table></body></html>"""

    def _listing(self, name: str) -> str:
        """Return a listing whose reported item count matches its rows.

        The recorded fixtures hold an excerpt of the listings of the ITU-T
        web site, so the number of items they report is the number of the
        whole listing.
        """
        page = self._read(name)
        rows = page.count('name="chkFile"')
        return re.sub(r"(Results:<strong>)\d+(</strong>)", rf"\g<1>{rows}\g<2>", page)
