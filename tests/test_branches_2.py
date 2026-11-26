"""Tests for the last branches of the package."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from itu_doc_downloader.api import ItuDocuments
from itu_doc_downloader.auth.ties import LOGON_URL, SAML_REQUEST_FIELD, SAML_RESPONSE_FIELD, AuthenticationError
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType
from itu_doc_downloader.scraping import detail, listing, meetings, questions
from tests.fakes import FakeClient

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def test_parse_files_ignores_a_duplicate_url() -> None:
    """The same rendition is only reported once."""
    link = '<a href="/dms_inf/x!!MSW-E.docx">Word</a>'
    page = (
        f"<html><body><table><tr><td>English</td><td>{link}</td><td>1 bytes</td><td>2026-01-01</td></tr>"
        f"<tr><td>English</td><td>{link}</td><td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1


def test_parse_files_ignores_a_link_without_a_format() -> None:
    """A link that carries no format suffix is ignored."""
    page = (
        "<html><body><table><tr><td>English</td>"
        '<td><a href="/dms_inf/x!!ABC">Word</a><a href="/dms_inf/y!!MSW-E.docx">Word</a></td>'
        "<td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1
    assert files[0].url.endswith("!!MSW-E.docx")


def test_parse_files_keeps_an_absolute_url() -> None:
    """An absolute download URL is kept as it is."""
    page = (
        "<html><body><table><tr><td>English</td>"
        '<td><a href="https://www.itu.int/dms_inf/x!!MSW-E.docx">Word</a></td>'
        "<td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert files[0].url == "https://www.itu.int/dms_inf/x!!MSW-E.docx"


def test_parse_date_of_a_rendition_that_cannot_be_read() -> None:
    """A posted date that cannot be read is reported as missing."""
    assert detail._parse_date("not a date") is None  # noqa: SLF001


def test_parse_other_meetings_skips_an_unreadable_code() -> None:
    """A meeting code that cannot be read is skipped."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?parent=T25-SG12-999999-TD">x</a></td></body></html>'

    assert listing.parse_other_meetings(page) == []


def test_parse_other_meetings_reports_a_meeting_once() -> None:
    """A meeting that is linked twice is reported once."""
    link = '<a href="/md/meetingdoc.asp?parent=T25-SG12-270119-TD">x</a>'
    page = f"<html><body><td>Other Meetings : {link}{link}</td></body></html>"

    assert [meeting.code for meeting in listing.parse_other_meetings(page)] == ["270119"]


def test_meeting_index_skips_an_unreadable_meeting_code() -> None:
    """A meeting link with an unreadable code is skipped."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-999999">Geneva, 1 January 2027</a></body></html>'

    assert meetings.parse_meeting_index(page) == []


def test_text_with_breaks_follows_nested_elements() -> None:
    """A nested element contributes its text and its tail."""
    page = (
        "<html><body><table><tr>"
        '<td><span id="lblQWP_1">Q1/12  (PLEN)</span><span id="lblQuestion_1">A question</span></td>'
        '<td><span id="lblFName_1">Ada</span><span id="lblLName_1">LOVELACE</span>'
        '<span id="lblRole_1">Rapporteur</span>'
        '<span id="lblAddress_1"><b>Seoul</b><br/><b>Korea (Rep. of)</b></span></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert parsed[0].people[0].country == "Korea (Rep. of)"


def test_find_documents_filters_by_every_criterion(tmp_path: Path, fake_client: FakeClient) -> None:
    """Every filter of the document search can be combined."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    api.sync_meeting(12, MeetingId.from_code("260609"), PERIOD, (DocType.CONTRIBUTION,))

    records = api.find_documents(
        study_group=12,
        study_period="2025-2028",
        doc_type=DocType.CONTRIBUTION,
        doc_types=(DocType.CONTRIBUTION,),
        meeting="260609",
        question=7,
        source="TU Berlin",
        limit=1,
    )

    assert len(records) == 1
    assert records[0].document_id == "T25-SG12-C-0192"


def test_top_sources_skips_other_meetings(tmp_path: Path, fake_client: FakeClient) -> None:
    """Meetings that are not asked for are left out of the count."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    api.sync_meeting(12, MeetingId.from_code("260609"), PERIOD, (DocType.CONTRIBUTION,))

    assert api.top_sources(study_group=12, meetings=("270119",)) == []


def test_download_writes_a_cached_document_to_an_output_path(tmp_path: Path, fake_client: FakeClient) -> None:
    """A cached document is copied to the requested output path."""
    from itu_doc_downloader.models.documents import DocumentRef
    from itu_doc_downloader.models.enums import DocFormat, DocLanguage

    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    document = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )
    api.cache.store(document, DocFormat.WORD, DocLanguage.ENGLISH, b"cached")
    output = tmp_path / "out" / "document.docx"

    path = api.download(document, DocFormat.WORD, DocLanguage.ENGLISH, output=output)

    assert path == output
    assert output.read_bytes() == b"cached"


def test_download_serves_a_cached_document(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document that was downloaded before is served from the cache."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    ref = MeetingId.from_code("261015")
    assert ref.code == "261015"

    from itu_doc_downloader.models.documents import DocumentRef

    document = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )
    from itu_doc_downloader.models.enums import DocFormat, DocLanguage

    api.cache.store(document, DocFormat.WORD, DocLanguage.ENGLISH, b"cached")

    path = api.download(document, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.read_bytes() == b"cached"


def test_authenticator_follows_a_redirect_without_a_location() -> None:
    """A redirect without a target ends the handshake."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(302)
        return httpx.Response(200, text=f'<form action="x"><input name="{SAML_REQUEST_FIELD}" value="y"/></form>')

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)

    from itu_doc_downloader.auth.ties import TiesAuthenticator

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_authenticator_reports_a_failed_status() -> None:
    """A failing status code is reported."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(403, text="denied")
        return httpx.Response(200, text=f'<form action="x"><input name="{SAML_REQUEST_FIELD}" value="y"/></form>')

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)

    from itu_doc_downloader.auth.ties import TiesAuthenticator

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError, match="HTTP 403"):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_saml_response_form_is_found() -> None:
    """The SAML response form of a page is found."""
    page = f'<form action="https://auth.itu.int/acs"><input name="{SAML_RESPONSE_FIELD}" value="z"/></form>'

    from itu_doc_downloader.auth.ties import find_saml_form

    form = find_saml_form(page, SAML_RESPONSE_FIELD)

    assert form is not None
    assert form[0] == "https://auth.itu.int/acs"


def test_date_of_a_meeting_is_read_from_the_page() -> None:
    """The start date of a meeting is part of its information."""
    info = meetings.MeetingInfo(MeetingId.from_code("261015"), "E-Meeting", date(2026, 10, 15), date(2026, 10, 16))

    assert info.end_date == date(2026, 10, 16)
