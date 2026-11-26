"""Tests for the edge cases of the parsers, the API and the interfaces."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from itu_doc_downloader.api import ItuDocuments
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType
from itu_doc_downloader.scraping import detail, listing, meetings, questions
from tests.fakes import FakeClient

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


@pytest.fixture
def api(tmp_path: Path, fake_client: FakeClient) -> ItuDocuments:
    """Return an API backed by the recorded fixtures."""
    return ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)


# ----------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------


def test_parse_total_items() -> None:
    """The number of items of a listing is read from the page."""
    page = "<html><body>Results:<strong>85</strong> total items.</body></html>"

    assert listing.parse_total_items(page) == 85


def test_parse_total_items_without_a_count() -> None:
    """A page without a result count yields nothing."""
    assert listing.parse_total_items("<html><body>no results here</body></html>") is None


def test_parse_meeting_header() -> None:
    """The header of a meeting page names the period, the dates and the place."""
    page = (
        "<html><body><p>Study Period 2025</p><p><strong>Meeting  from  2026-06-09 to 2026-06-17</strong></p><p> held in Switzerland [Geneva]</p></body></html>"
    )

    header = listing.parse_meeting_header(page)

    assert header["study_period"] == "2025"
    assert header["start_date"] == "2026-06-09"
    assert header["end_date"] == "2026-06-17"


def test_parse_detail_page_without_files() -> None:
    """A detail page without renditions yields no file."""
    assert detail.parse_files("<html><body>no files</body></html>") == []


def test_parse_detail_page_without_a_title() -> None:
    """A detail page without a heading yields no title."""
    assert detail.parse_title("<html><body>nothing</body></html>") == ""


def test_parse_meeting_text_of_a_cross_month_range() -> None:
    """A meeting that spans two months is parsed."""
    parsed = meetings._parse_meeting_text("Geneva, 28 November - 6 December 2025")  # noqa: SLF001
    assert parsed is not None
    place, start, end = parsed

    assert place == "Geneva"
    assert start == date(2025, 11, 28)
    assert end == date(2025, 12, 6)


def test_parse_meeting_text_of_an_unparsable_value() -> None:
    """A meeting link without a readable date is ignored."""
    assert meetings._parse_meeting_text("somewhere else") is None  # noqa: SLF001


def test_parse_meeting_index_of_a_page_without_meetings() -> None:
    """A page without meetings yields no meeting."""
    assert meetings.parse_meeting_index("<html><body>nothing</body></html>") == []


def test_parse_questions_of_a_page_without_questions() -> None:
    """A page without questions yields no question."""
    assert questions.parse_questions("<html><body>nothing</body></html>", 12) == []


def test_parse_question_numbers_of_a_page_without_questions() -> None:
    """A page without questions yields no question number."""
    assert meetings.parse_question_numbers("<html><body>nothing</body></html>") == []


def test_parse_listing_of_a_page_without_documents() -> None:
    """A page without documents yields no document."""
    assert listing.parse_listing("<html><body>nothing</body></html>", PERIOD, 12, DocType.CONTRIBUTION) == []


def test_parse_questions_with_an_unknown_role() -> None:
    """A role that the ITU-T pages do not know becomes a contributor."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12  (PLEN)</span>'
        '<span id="lblQuestion_1">A question</span></td>'
        '<td><span id="lblFName_1">Ada</span><span id="lblLName_1">LOVELACE</span>'
        '<span id="lblRole_1">Observer</span></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert len(parsed) == 1
    assert parsed[0].people[0].role.value == "Contributor"


def test_parse_questions_without_a_person() -> None:
    """A question without a person yields no person."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12  (PLEN)</span><span id="lblQuestion_1">A question</span></td><td></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert len(parsed) == 1
    assert parsed[0].people == []


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------


def test_study_period_rejects_a_reversed_period() -> None:
    """A period that ends before it starts is rejected."""
    with pytest.raises(ValueError):
        StudyPeriod(start_year=2028, end_year=2025)


def test_document_ref_of_a_temporary_document_without_a_subtype() -> None:
    """A temporary document without a sub-type uses the general one."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=1,
        meeting=MeetingId.from_code("261015"),
    )

    assert ref.document_id == "T25-SG12-261015-TD-GEN-0001"


def test_document_ref_of_a_temporary_document_without_a_meeting() -> None:
    """A temporary document without a meeting has no download URL."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=1,
    )

    with pytest.raises(ValueError):
        _ = ref.download_url(DocFormat.PDF, DocLanguage.ENGLISH)


def test_document_file_without_a_known_format() -> None:
    """A file with an unknown format code has no extension."""
    from itu_doc_downloader.models.documents import DocumentFile

    rendition = DocumentFile(format_code="XYZ", language_code="Q", url="https://example.org")

    assert rendition.file_format is None
    assert rendition.language is None
    assert rendition.extension == ""


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------


def test_sync_questions(api: ItuDocuments) -> None:
    """The questions of a study group are stored."""
    assert api.sync_questions(12, PERIOD) == 5


def test_sync_detail(api: ItuDocuments) -> None:
    """The renditions of a document are fetched and stored."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    metadata = api.sync_detail(ref)

    assert metadata.files
    assert metadata.files[0].format_code == "MSW"


def test_download_uses_the_cache(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document that was downloaded before is served from the cache."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    assert path.read_bytes() == b"document-bytes"
    assert client.requested

    again = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    assert again == path
    assert len([url for url in client.requested if url.endswith(".docx")]) == 1
    assert client.login_targets == [client.requested[-1]]


def test_download_writes_to_an_output_path(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document can be written to a chosen path."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )
    output = tmp_path / "out" / "document.docx"

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH, output=output)

    assert path == output
    assert output.read_bytes() == b"document-bytes"


def test_download_of_an_unavailable_rendition(tmp_path: Path, fake_client: FakeClient) -> None:
    """A rendition that the ITU-T does not offer is reported."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    with pytest.raises(FileNotFoundError):
        api.download(ref, DocFormat.PDF, DocLanguage.ENGLISH)


def test_api_context_manager_closes_the_client(tmp_path: Path, fake_client: FakeClient) -> None:
    """The API closes the client it owns."""
    with ItuDocuments(Settings(cache_dir=tmp_path)) as owned:
        assert owned.client is not None


# ----------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------


def test_authenticate_uses_the_credentials(tmp_path: Path) -> None:
    """A login is performed when credentials are configured."""
    Settings(cache_dir=tmp_path, ties_username="you@example.org", ties_password="secret")
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)), follow_redirects=True)

    from itu_doc_downloader.auth.ties import TiesAuthenticator

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")
    assert authenticator.is_authenticated is False
    client.close()
