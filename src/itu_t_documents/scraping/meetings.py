"""Parser for the ITU-T study group meeting index pages.

The page ``/md/T{period}-SG{group}/en`` lists every meeting of a study group
together with its place and dates, and links to the document types of the
meeting.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Final

from itu_t_documents.models.documents import MeetingId
from itu_t_documents.scraping.pages import parse_page, scraping_error

#: Names of the months as used by the ITU-T pages, in several spellings.
_MONTH_NUMBERS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
)
MONTHS: Final[Mapping[str, int]] = MappingProxyType(
    {
        **_MONTH_NUMBERS,
        **{name[:3]: number for name, number in _MONTH_NUMBERS.items()},
        "sept": 9,
    }
)

#: Pattern of the meeting link, e.g. ``/md/meeting.asp?…&parent=T25-SG12-270119``.
_MEETING_LINK_RE = re.compile(r"parent=T\d{2}-SG\d{1,3}-(?P<code>\d{6})")

#: Pattern of a same month date range, e.g. ``Geneva, 19 - 27 January 2027``.
_SAME_MONTH_RE = re.compile(r"^(?P<place>.+?),\s*(?P<first>\d{1,2})\s*-\s*(?P<second>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})$")

#: Pattern of a date range across months or years, e.g. ``Geneva, 28 November -
#: 6 December 2025`` or ``Geneva, 15 December 2025 - 9 January 2026``.
_CROSS_MONTH_RE = re.compile(
    r"^(?P<place>.+?),\s*(?P<first>\d{1,2})\s+(?P<first_month>[A-Za-z]+)"
    r"(?:\s+(?P<first_year>\d{4}))?\s*-\s*"
    r"(?P<second>\d{1,2})\s+(?P<second_month>[A-Za-z]+)\s+(?P<year>\d{4})$"
)

#: Pattern of a single day meeting, e.g. ``E-Meeting, 15 October 2026``.
_SINGLE_DAY_RE = re.compile(r"^(?P<place>.+?),\s*(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})$")

#: Pattern of the question links of the study group.
_QUESTION_RE = re.compile(r"Q(?P<number>\d+)/(?P<group>\d+)")


@dataclass(frozen=True, repr=False)
class MeetingInfo:
    """A meeting of a study group as listed on the meeting index page."""

    meeting: MeetingId
    place: str
    start_date: date
    end_date: date | None = None

    @property
    def code(self) -> str:
        """The DMS code of the meeting, e.g. ``270119``."""
        return self.meeting.code

    @property
    def label(self) -> str:
        """A human readable description of the meeting."""
        if self.end_date is None or self.end_date == self.start_date:
            return f"{self.place}, {self.start_date.strftime('%d %B %Y')}"
        return f"{self.place}, {self.start_date.strftime('%d %B')} - {self.end_date.strftime('%d %B %Y')}"

    def __repr__(self) -> str:
        """Return a debugging representation of the meeting."""
        return f"MeetingInfo({self.code!r}, {self.label!r})"


def parse_meeting_index(page_html: str) -> list[MeetingInfo]:
    """Parse the meeting index page of a study group.

    Args:
        page_html: The HTML of the meeting index page.

    Returns:
        The meetings found, in the order of the page.

    Raises:
        ScrapingError: When a meeting link cannot be read.
    """
    tree = parse_page(page_html)
    if tree is None:
        raise scraping_error("meeting index", page_html)
    meetings: list[MeetingInfo] = []
    for link in tree.xpath("//a[starts-with(@href, '/md/meeting.asp')]"):
        text = link.text_content()
        link_text = f"{text} {link.get('href') or ''}"
        match = _MEETING_LINK_RE.search(link.get("href") or "")
        if match is None:
            raise scraping_error("meeting link", link_text)
        place, start_date, end_date = _parse_meeting_text(text)
        try:
            meeting = MeetingId.from_code(match["code"])
        except ValueError as error:
            raise scraping_error("meeting link", link_text) from error
        meetings.append(MeetingInfo(meeting, place, start_date, end_date))
    return meetings


def _parse_meeting_text(text: str) -> tuple[str, date, date | None]:
    """Parse the place and the dates out of a meeting link.

    Raises:
        ScrapingError: When the date is not one the ITU-T pages use.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    match = _SAME_MONTH_RE.match(cleaned)
    if match is not None:
        month = _month(match["month"], cleaned)
        year = int(match["year"])
        return (
            match["place"].strip(),
            _date(year, month, int(match["first"]), cleaned),
            _date(year, month, int(match["second"]), cleaned),
        )
    match = _CROSS_MONTH_RE.match(cleaned)
    if match is not None:
        first_year = int(match["first_year"]) if match["first_year"] else int(match["year"])
        return (
            match["place"].strip(),
            _date(first_year, _month(match["first_month"], cleaned), int(match["first"]), cleaned),
            _date(int(match["year"]), _month(match["second_month"], cleaned), int(match["second"]), cleaned),
        )
    match = _SINGLE_DAY_RE.match(cleaned)
    if match is not None:
        start = _date(int(match["year"]), _month(match["month"], cleaned), int(match["day"]), cleaned)
        return match["place"].strip(), start, None
    raise scraping_error("meeting date", cleaned)


def _month(name: str, text: str) -> int:
    """Look up a month name as the ITU-T pages write it."""
    number = MONTHS.get(name.lower())
    if number is None:
        raise scraping_error("meeting date", text)
    return number


def _date(year: int, month: int, day: int, text: str) -> date:
    """Build a date, refusing the impossible days untrusted pages may carry."""
    try:
        return date(year, month, day)
    except ValueError as error:
        raise scraping_error("meeting date", text) from error


def parse_question_numbers(page_html: str) -> list[int]:
    """Parse the question numbers listed on a meeting index page.

    Args:
        page_html: The HTML of the meeting index page.

    Returns:
        The question numbers found, in ascending order.
    """
    numbers: set[int] = set()
    for match in _QUESTION_RE.finditer(page_html):
        numbers.add(int(match["number"]))
    return sorted(numbers)
