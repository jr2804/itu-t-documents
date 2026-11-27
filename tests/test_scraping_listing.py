"""Tests for the parser of the document listings."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from itu_t_documents.errors import ScrapingError
from itu_t_documents.models.documents import MeetingId
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.metadata import MeetingHeader
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping import listing, questions
from itu_t_documents.scraping.pages import parse_page


def test_parse_contribution_listing(fixtures_dir: Path) -> None:
    """A contribution listing yields the documents with their metadata."""
    page = _read(fixtures_dir, "listing_contributions.html")

    documents = listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION, MeetingId.from_code("260609"))

    assert len(documents) == 3
    first = documents[0]
    assert first.document_id == "T25-SG12-C-0192"
    assert first.title.startswith("Proposal for a machine-learning speech dataset")
    assert first.sources == ["Technische Universität Berlin (TU Berlin) (Germany)"]
    assert first.questions == [7]
    assert first.posted == date(2026, 5, 27)
    assert first.ref.meeting is not None
    assert first.ref.meeting.code == "260609"


def test_parse_temporary_document_listing(fixtures_dir: Path) -> None:
    """A temporary document listing yields the documents of a meeting."""
    page = _read(fixtures_dir, "listing_temporary_documents.html")

    documents = listing.parse_listing(page, PERIOD, 12, DocType.TEMPORARY_DOCUMENT, MeetingId.from_code("261015"))

    assert documents
    assert all(document.document_id.startswith("T25-SG12-261015-TD-") for document in documents)
    assert all(document.ref.subtype == "GEN" for document in documents)


def test_parse_report_listing_spanning_two_pages(fixtures_dir: Path) -> None:
    """A listing that spans several pages holds a part of its documents on each page."""
    first_page = _read(fixtures_dir, "listing_reports_first_page.html")
    last_page = _read(fixtures_dir, "listing_reports_last_page.html")

    first_documents = listing.parse_listing(first_page, PERIOD, 12, DocType.REPORT)
    last_documents = listing.parse_listing(last_page, PERIOD, 12, DocType.REPORT)

    assert [document.ref.number for document in first_documents] == [14, 13, 12, 11, 10, 9, 8, 7, 6, 5]
    assert [document.ref.number for document in last_documents] == [4, 3, 2, 1]
    assert listing.parse_total_items(first_page) == listing.parse_total_items(last_page) == 14


def test_parse_next_page(fixtures_dir: Path) -> None:
    """Every page but the last one links to the next page."""
    first_page = _read(fixtures_dir, "listing_reports_first_page.html")
    last_page = _read(fixtures_dir, "listing_reports_last_page.html")

    assert listing.parse_next_page(first_page) == "/md/meetingdoc.asp?lang=en&parent=T25-SG12-R&PageLB=10"
    assert listing.parse_next_page(last_page) is None
    assert listing.parse_next_page(_read(fixtures_dir, "listing_contributions.html")) is None
    assert listing.parse_next_page("") is None


def test_parse_subtypes_of_a_temporary_document_listing(fixtures_dir: Path) -> None:
    """A listing offers the listing of every sub-type of the meeting."""
    page = _read(fixtures_dir, "listing_temporary_documents.html")

    subtypes = listing.parse_subtypes(page, MeetingId.from_code("261015"))

    assert subtypes == ["GEN"]


def test_parse_subtypes_of_another_meeting(fixtures_dir: Path) -> None:
    """The sub-types of the other meetings are not offered."""
    page = _read(fixtures_dir, "listing_temporary_documents.html")

    assert listing.parse_subtypes(page, MeetingId.from_code("260609")) == []


def test_parse_subtypes_of_an_empty_page() -> None:
    """An empty page is refused instead of being read as an empty list."""
    with pytest.raises(ScrapingError, match="temporary document sub-types"):
        listing.parse_subtypes("", MeetingId.from_code("261015"))


def test_parse_page_of_broken_markup() -> None:
    """A page that holds no markup at all is reported as such."""
    assert parse_page("") is None
    assert parse_page("   ") is None
    assert parse_page("<html><body><p>text</p></body></html>") is not None
    assert parse_page("<html") is None


def test_listing_without_a_document_table_is_refused() -> None:
    """A page that holds no document table is not an empty listing."""
    page = "<html><body><p>Server error</p></body></html>"

    with pytest.raises(ScrapingError, match="document listing"):
        listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION)


def test_listing_refuses_a_row_without_an_identifier() -> None:
    """A row the ITU-T cannot name is refused with its text."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td></tr></table></body></html>"
    )

    with pytest.raises(ScrapingError, match="document listing row"):
        listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION)


def test_listing_refuses_an_unparsable_identifier() -> None:
    """An identifier that does not follow the DMS format is refused."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" id="nonsense" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td></tr></table></body></html>"
    )

    with pytest.raises(ScrapingError, match="document listing row"):
        listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION)


def test_other_meetings_refuses_an_invalid_date_link() -> None:
    """A date-labelled link with an invalid meeting code is visible."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?parent=T25-SG12-999999-TD">2027-01-19</a></td></body></html>'

    with pytest.raises(ScrapingError, match="other meetings link"):
        listing.parse_other_meetings(page)


def test_other_meetings_refuses_a_date_link_without_a_code() -> None:
    """A date-labelled link that names no meeting is visible."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?parent=T25-SG12">2027-01-19</a></td></body></html>'

    with pytest.raises(ScrapingError, match="other meetings link"):
        listing.parse_other_meetings(page)


def test_meeting_header_is_a_frozen_value(fixtures_dir: Path) -> None:
    """The header is a value object with optional fields."""
    header = listing.parse_meeting_header(_read(fixtures_dir, "listing_temporary_documents.html"))

    assert isinstance(header, MeetingHeader)
    assert header.study_period == "2025"
    assert header.start_date == date(2026, 10, 15)
    assert header.end_date == date(2026, 10, 15)
    assert header.place == "E-Meeting"
    with pytest.raises(ValidationError):
        header.__setattr__("place", "elsewhere")


def test_parse_other_meetings(fixtures_dir: Path) -> None:
    """A listing page lists the other meetings of the study group."""
    page = _read(fixtures_dir, "listing_temporary_documents.html")

    found = listing.parse_other_meetings(page)

    assert "270119" in {meeting.code for meeting in found}
    assert "250114" in {meeting.code for meeting in found}


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


PERIOD = StudyPeriod(start_year=2025, end_year=2028)


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

    assert header.study_period == "2025"
    assert header.start_date == date(2026, 6, 9)
    assert header.end_date == date(2026, 6, 17)


def test_parse_listing_skips_a_row_without_an_identifier() -> None:
    """A row without a document identifier is ignored."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td><td>Q5/12</td><td>2026-05-27</td></tr></table></body></html>"
    )

    with pytest.raises(ScrapingError, match="document listing row"):
        listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION)


def test_parse_other_meetings_skips_an_unreadable_code() -> None:
    """A meeting code that cannot be read is skipped."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?parent=T25-SG12-999999-TD">x</a></td></body></html>'

    assert listing.parse_other_meetings(page) == []


def test_parse_other_meetings_reports_a_meeting_once() -> None:
    """A meeting that is linked twice is reported once."""
    link = '<a href="/md/meetingdoc.asp?parent=T25-SG12-270119-TD">2027-01-19</a>'
    page = f"<html><body><td>Other Meetings : {link}{link}</td></body></html>"

    assert [meeting.code for meeting in listing.parse_other_meetings(page)] == ["270119"]


def test_parse_listing_skips_a_row_with_an_unparsable_identifier() -> None:
    """A row with an unparsable document identifier is ignored."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" id="nonsense" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td><td>Q5/12</td><td>2026-05-27</td></tr></table></body></html>"
    )

    with pytest.raises(ScrapingError, match="document listing row"):
        listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION)


def test_parse_other_meetings_skips_links_without_a_meeting() -> None:
    """Links that name no meeting are ignored."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?lang=en&amp;parent=T25-SG12-C">x</a></td></body></html>'

    assert listing.parse_other_meetings(page) == []


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


def test_parse_meeting_header_without_a_place() -> None:
    """A header without a place yields no place."""
    page = "<html><body><p>Study Period 2025</p></body></html>"

    header = listing.parse_meeting_header(page)

    assert header.study_period == "2025"
    assert header.start_date is None
    assert header.end_date is None
    assert header.place is None


def test_parse_listing_of_a_page_without_documents() -> None:
    """A page without documents is refused instead of becoming an empty listing."""
    with pytest.raises(ScrapingError, match="document listing"):
        listing.parse_listing("<html><body>nothing</body></html>", PERIOD, 12, DocType.CONTRIBUTION)


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

    assert listing.parse_meeting_header(page).place == "Switzerland [Geneva]"
