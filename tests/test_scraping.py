"""Tests for the parsers of the ITU-T meeting document pages."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from itu_doc_downloader.models.documents import MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType
from itu_doc_downloader.scraping import detail, listing, meetings, questions

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


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


def test_parse_detail_page(fixtures_dir: Path) -> None:
    """A detail page yields the available renditions of a document."""
    page = _read(fixtures_dir, "detail_temporary_document.html")

    files = detail.parse_files(page)

    assert len(files) == 1
    rendition = files[0]
    assert rendition.format_code == "MSW"
    assert rendition.language_code == "E"
    assert rendition.size_bytes == 46104
    assert rendition.posted == date(2026, 10, 9)
    assert rendition.url == ("https://www.itu.int/dms_inf/itu-t/md/25/sg12/td/261015/GEN/T25-SG12-261015-TD-GEN-0520!!MSW-E.docx")


def test_parse_detail_page_title(fixtures_dir: Path) -> None:
    """A detail page yields the title of a document."""
    page = _read(fixtures_dir, "detail_temporary_document.html")

    assert detail.parse_title(page) == "Draft agenda for WP1/12: Terminals and multimedia subjective assessment"


def test_parse_page_of_broken_markup() -> None:
    """A page that holds no markup at all is reported as such."""
    from itu_doc_downloader.scraping.pages import parse_page

    assert parse_page("") is None
    assert parse_page("   ") is None
    assert parse_page("<html><body><p>text</p></body></html>") is not None
    assert parse_page("<html") is None


def test_parsers_survive_an_empty_page() -> None:
    """The ITU-T answers some requests with an empty body."""
    assert listing.parse_listing("", PERIOD, 12, DocType.CONTRIBUTION) == []
    assert listing.parse_other_meetings("") == []
    assert listing.parse_meeting_header("") == {}
    assert detail.parse_files("") == []
    assert detail.parse_title("") == ""
    assert meetings.parse_meeting_index("") == []
    assert questions.parse_questions("", 12) == []


def test_parse_questions_page(fixtures_dir: Path) -> None:
    """The questions page yields the questions with their working group and people."""
    page = _read(fixtures_dir, "questions.html")

    parsed = questions.parse_questions(page, 12)

    assert len(parsed) == 5
    first = parsed[0]
    assert first.code == "Q1/12"
    assert first.working_group.code == "PLEN"
    assert first.working_group.is_plenary
    assert first.people[0].name == "Seong-Ho JEONG"
    assert first.people[0].role.value == "Co-rapporteur"
    assert first.people[0].country == "Korea (Rep. of)"

    question_five = next(item for item in parsed if item.number == 5)
    assert question_five.working_group.code == "WP1/12"
    assert question_five.rapporteurs[0].name == "Lars Birger NIELSEN"
    assert question_five.rapporteurs[0].country == "Denmark"

    question_four = next(item for item in parsed if item.number == 4)
    assert question_four.rapporteurs[0].email == "jan.reimes@head-acoustics.de"


def test_parse_meeting_index(fixtures_dir: Path) -> None:
    """The meeting index yields the meetings of a study group."""
    page = _read(fixtures_dir, "meeting_index.html")

    parsed = meetings.parse_meeting_index(page)

    assert [meeting.code for meeting in parsed] == ["270119", "261015", "260609", "250909", "250325", "250114"]
    assert parsed[0].place == "Geneva"
    assert parsed[0].start_date == date(2027, 1, 19)
    assert parsed[0].end_date == date(2027, 1, 27)
    assert parsed[1].place == "E-Meeting"
    assert parsed[1].end_date is None


def test_parse_question_numbers(fixtures_dir: Path) -> None:
    """The meeting index lists the questions of the study group."""
    page = _read(fixtures_dir, "meeting_index.html")

    assert meetings.parse_question_numbers(page)[:3] == [1, 2, 4]


def test_parse_other_meetings(fixtures_dir: Path) -> None:
    """A listing page lists the other meetings of the study group."""
    page = _read(fixtures_dir, "listing_temporary_documents.html")

    found = listing.parse_other_meetings(page)

    assert "270119" in {meeting.code for meeting in found}
    assert "250114" in {meeting.code for meeting in found}
