"""Tests for the remaining branches of the package."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from itu_doc_downloader.auth.ties import LOGON_URL, SAML_REQUEST_FIELD, AuthenticationError
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.http.client import ItuHttpClient
from itu_doc_downloader.models.documents import StudyPeriod
from itu_doc_downloader.scraping import detail, listing, meetings
from tests.fakes import FakeClient

SAML_REQUEST_PAGE = f"""<html><body><form action="https://login.itu.int/saml/idp/profile/redirectorpost/sso">
<input type="hidden" name="{SAML_REQUEST_FIELD}" value="PHNhbWw+"/></form></body></html>"""

SAML_RESPONSE_PAGE = """<html><body><form action="https://auth.itu.int/saml/sp/profile/post/acs">
<input type="hidden" name="{SAML_RESPONSE_FIELD}" value="PHNhbWw+"/></form></body></html>"""

DUMMY_PAGE = """<html><body onload="document.forms[0].submit()">
<form method="POST" action="https://login.itu.int/saml/idp/profile/redirectorpost/sso">
<input type="hidden" name="dummy" value="92b6ecc7"/></form></body></html>"""


def _itu_handler(request: httpx.Request) -> httpx.Response:
    """Simulate the ITU-T access policy and its identity provider."""
    url = str(request.url)
    if request.method == "GET" and ("auth.itu.int" in url or url.startswith("https://www.itu.int/md/")):
        return httpx.Response(200, text=SAML_REQUEST_PAGE)
    if request.method == "POST" and "redirectorpost" in url:
        if b"SAMLRequest" in request.content:
            return httpx.Response(200, text="<html><body>logon</body></html>")
        return httpx.Response(200, text=SAML_RESPONSE_PAGE)
    if request.method == "POST" and url == LOGON_URL:
        return httpx.Response(200, text=DUMMY_PAGE)
    if request.method == "POST" and "post/acs" in url:
        return httpx.Response(302, headers={"location": "https://www.itu.int/md/"})
    return httpx.Response(200, content=b"page")


def test_http_client_authenticates_with_credentials(tmp_path) -> None:
    """A login is performed with the configured credentials."""
    settings = Settings(cache_dir=tmp_path, ties_username="you@example.org", ties_password="secret")
    client = ItuHttpClient(settings)
    client._session_client = httpx.Client(  # noqa: SLF001
        transport=httpx.MockTransport(_itu_handler),
        follow_redirects=True,
    )

    session = client.authenticate()

    assert session is client.session_client
    client.close()


def test_http_client_reuses_the_authenticator(tmp_path) -> None:
    """A second login reuses the authenticator of the client."""
    settings = Settings(cache_dir=tmp_path, ties_username="you@example.org", ties_password="secret")
    client = ItuHttpClient(settings)
    client._session_client = httpx.Client(  # noqa: SLF001
        transport=httpx.MockTransport(_itu_handler),
        follow_redirects=True,
    )

    client.authenticate()
    authenticator = client._authenticator  # noqa: SLF001
    client.authenticate()

    assert client._authenticator is authenticator  # noqa: SLF001
    client.close()


def test_authenticator_reports_a_server_error() -> None:
    """A server error during the handshake is reported."""

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = httpx.Client(transport=httpx.MockTransport(failing), follow_redirects=True)

    from itu_doc_downloader.auth.ties import TiesAuthenticator

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_cli_mcp_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mcp command starts the MCP server."""
    from itu_doc_downloader.cli import commands

    started: list[bool] = []
    monkeypatch.setattr(commands, "run_mcp", lambda: started.append(True))

    commands.mcp()

    assert started == [True]


def test_settings_source_reports_unset_fields() -> None:
    """The TOML source never sets a field on its own."""
    from pydantic.fields import FieldInfo

    from itu_doc_downloader.config.settings import TomlConfigSource

    source = TomlConfigSource(Settings, Path(__file__))

    value, name, complex_ = source.get_field_value(FieldInfo(annotation=int), "timeout")

    assert value is None
    assert name == "timeout"
    assert not complex_


def test_mcp_period_with_an_explicit_label() -> None:
    """The MCP tools accept an explicit study period."""
    from itu_doc_downloader.mcp_server import _period

    assert _period("2017-2020").label == "2017-2020"
    assert _period(None).label == "2025-2028"


def test_mcp_sync_skips_an_invalid_meeting_code(tmp_path: Path, fake_client: FakeClient) -> None:
    """A meeting code that cannot be read is skipped."""
    from itu_doc_downloader import mcp_server
    from itu_doc_downloader.api import ItuDocuments

    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)

    assert mcp_server._sync_meetings(api, 12, StudyPeriod(start_year=2025, end_year=2028), ["abc"]) == []


def test_parse_files_reads_every_rendition() -> None:
    """Every rendition of a row is read."""
    page = (
        "<html><body><table><tr>"
        '<td>English</td><td><a href="/dms_inf/x!!MSW-E.docx">Word</a></td>'
        "<td>46104 bytes</td><td>2026-10-09</td><td>[520-GEN]</td>"
        "</tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1
    assert files[0].size_bytes == 46104
    assert files[0].posted == date(2026, 10, 9)


def test_parse_other_meetings_ignores_a_link_without_a_meeting() -> None:
    """A link that names no meeting is skipped."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?parent=T25-SG12">x</a></td></body></html>'

    assert listing.parse_other_meetings(page) == []


def test_parse_meeting_header_reads_the_place() -> None:
    """The place of a meeting is read from the header."""
    page = (
        "<html><body><p>Study Period 2025</p>"
        "<p><strong>Meeting  from  2026-06-09 to 2026-06-17</strong></p>"
        "<p> held in Switzerland [Geneva] Other Meetings</p></body></html>"
    )

    assert listing.parse_meeting_header(page)["place"] == "Switzerland [Geneva]"


def test_meeting_info_label_and_representation() -> None:
    """A meeting describes itself with a label."""
    info = meetings.MeetingInfo(
        meetings.MeetingId.from_code("261015"),
        "E-Meeting",
        date(2026, 10, 15),
        None,
    )

    assert info.code == "261015"
    assert info.label == "E-Meeting, 15 October 2026"
    assert "261015" in repr(info)


def test_meeting_info_label_of_a_multi_day_meeting() -> None:
    """A meeting that spans several days names the whole range."""
    info = meetings.MeetingInfo(
        meetings.MeetingId.from_code("270119"),
        "Geneva",
        date(2027, 1, 19),
        date(2027, 1, 27),
    )

    assert info.label == "Geneva, 19 January - 27 January 2027"


def test_meeting_index_skips_a_link_without_a_date() -> None:
    """A meeting link without a readable date is skipped."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-270119">somewhere</a></body></html>'

    assert meetings.parse_meeting_index(page) == []


def test_meeting_index_skips_an_unreadable_code() -> None:
    """A meeting link with an unreadable code is skipped."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-27011">Geneva</a></body></html>'

    assert meetings.parse_meeting_index(page) == []


def test_store_rejects_a_row_that_was_not_persisted() -> None:
    """A row without a primary key is refused."""
    from itu_doc_downloader.storage.database import _row_id

    class Unpersisted:
        """A row that was never written."""

        id = None

    with pytest.raises(RuntimeError):
        _row_id(Unpersisted())  # type: ignore[arg-type]


def test_meeting_row_unique_key() -> None:
    """The key of a meeting is unique across the store."""
    from itu_doc_downloader.storage.database import MeetingRow

    meeting = MeetingRow(study_group_id=3, code="270119", start_date=date(2027, 1, 19))

    assert meeting.unique_key == "3:270119"
