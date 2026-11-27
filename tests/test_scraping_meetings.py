"""Tests for the parser of the meeting index."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from itu_t_documents.errors import ScrapingError
from itu_t_documents.scraping import meetings


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


@pytest.mark.parametrize(
    ("text", "expected_month"),
    [
        ("Geneva, 19 - 27 January 2027", 1),
        ("Geneva, 19 - 27 September 2027", 9),
        ("Geneva, 19 - 27 Sept 2027", 9),
        ("Geneva, 19 - 27 OCTOBER 2027", 10),
        ("Geneva, 19 - 27 Dec 2027", 12),
    ],
)
def test_meeting_dates_accept_the_spellings_of_the_pages(text: str, expected_month: int) -> None:
    """Abbreviated and upper-case month names are read as the ITU-T writes them."""
    place, start, end = meetings._parse_meeting_text(text)

    assert place == "Geneva"
    assert start == date(2027, expected_month, 19)
    assert end == date(2027, expected_month, 27)


def test_meeting_dates_span_two_years() -> None:
    """A meeting that runs into the next year keeps both years."""
    place, start, end = meetings._parse_meeting_text("Geneva, 15 December 2025 - 9 January 2026")

    assert place == "Geneva"
    assert start == date(2025, 12, 15)
    assert end == date(2026, 1, 9)


@pytest.mark.parametrize(
    "text",
    [
        "Geneva, 32 January 2027",
        "Geneva, 19 - 27 Foo 2027",
        "Geneva, 19 February 2027 - 27 March",
        "no date at all",
    ],
)
def test_meeting_dates_refuse_untrusted_text(text: str) -> None:
    """Impossible or unrecognised dates are reported with the text."""
    with pytest.raises(ScrapingError, match="meeting date"):
        meetings._parse_meeting_text(text)


def test_meeting_index_refuses_an_unreadable_link() -> None:
    """A meeting link whose code is not a real date is visible."""
    page = '<html><body><a href="/md/meeting.asp?parent=T25-SG12-999999">Geneva, 1 January 2027</a></body></html>'

    with pytest.raises(ScrapingError, match="meeting link"):
        meetings.parse_meeting_index(page)


def test_meeting_index_refuses_a_link_without_a_code() -> None:
    """A meeting link that names no meeting is visible."""
    page = '<html><body><a href="/md/meeting.asp?parent=T25-SG12">Geneva</a></body></html>'

    with pytest.raises(ScrapingError, match="meeting link"):
        meetings.parse_meeting_index(page)


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_parse_meeting_text_of_a_cross_month_range() -> None:
    """A meeting that spans two months is parsed."""
    parsed = meetings._parse_meeting_text("Geneva, 28 November - 6 December 2025")
    assert parsed is not None
    place, start, end = parsed

    assert place == "Geneva"
    assert start == date(2025, 11, 28)
    assert end == date(2025, 12, 6)


def test_parse_meeting_text_of_an_unparsable_value() -> None:
    """A meeting link without a readable date is reported."""
    with pytest.raises(ScrapingError, match="meeting date"):
        meetings._parse_meeting_text("somewhere else")


def test_parse_meeting_index_of_a_page_without_meetings() -> None:
    """A page without meetings yields no meeting."""
    assert meetings.parse_meeting_index("<html><body>nothing</body></html>") == []


def test_meeting_index_skips_an_unreadable_meeting_code() -> None:
    """A meeting link with an unreadable code is refused."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-999999">Geneva, 1 January 2027</a></body></html>'

    with pytest.raises(ScrapingError, match="meeting link"):
        meetings.parse_meeting_index(page)


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
    """A meeting link without a readable date is refused."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-270119">somewhere</a></body></html>'

    with pytest.raises(ScrapingError, match="meeting date"):
        meetings.parse_meeting_index(page)


def test_meeting_index_skips_an_unreadable_code() -> None:
    """A meeting link with an unreadable code is refused."""
    page = '<html><body><a href="/md/meeting.asp?lang=en&amp;parent=T25-SG12-27011">Geneva</a></body></html>'

    with pytest.raises(ScrapingError, match="meeting link"):
        meetings.parse_meeting_index(page)
