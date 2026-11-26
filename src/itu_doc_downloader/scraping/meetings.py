"""Parser for the ITU-T study group meeting index pages.

The page ``/md/T{period}-SG{group}/en`` lists every meeting of a study group
together with its place and dates, and links to the document types of the
meeting.
"""

from __future__ import annotations

import re
from datetime import date

from lxml import html

from itu_doc_downloader.models.documents import MeetingId

#: Names of the months as used by the ITU-T pages.
MONTHS: dict[str, int] = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

#: Pattern of the meeting link, e.g. ``/md/meeting.asp?…&parent=T25-SG12-270119``.
_MEETING_LINK_RE = re.compile(r"parent=T\d{2}-SG\d{1,3}-(?P<code>\d{6})")

#: Pattern of a same month date range, e.g. ``Geneva, 19 - 27 January 2027``.
_SAME_MONTH_RE = re.compile(r"^(?P<place>.+?),\s*(?P<first>\d{1,2})\s*-\s*(?P<second>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})$")

#: Pattern of a cross month date range, e.g. ``Geneva, 28 November - 6 December 2025``.
_CROSS_MONTH_RE = re.compile(
    r"^(?P<place>.+?),\s*(?P<first>\d{1,2})\s+(?P<first_month>[A-Za-z]+)\s*-\s*"
    r"(?P<second>\d{1,2})\s+(?P<second_month>[A-Za-z]+)\s+(?P<year>\d{4})$"
)

#: Pattern of a single day meeting, e.g. ``E-Meeting, 15 October 2026``.
_SINGLE_DAY_RE = re.compile(r"^(?P<place>.+?),\s*(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})$")

#: Pattern of the question links of the study group.
_QUESTION_RE = re.compile(r"Q(?P<number>\d+)/(?P<group>\d+)")


class MeetingInfo:
    """A meeting of a study group as listed on the meeting index page."""

    def __init__(self, meeting: MeetingId, place: str, start_date: date, end_date: date | None) -> None:
        """Create a meeting description.

        Args:
            meeting: The identifier of the meeting.
            place: Where the meeting is held.
            start_date: The first day of the meeting.
            end_date: The last day of the meeting, if the meeting spans several days.
        """
        self.meeting = meeting
        self.place = place
        self.start_date = start_date
        self.end_date = end_date

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


def _parse_meeting_text(text: str) -> tuple[str, date, date | None] | None:
    """Parse the place and the dates out of a meeting link."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    match = _SAME_MONTH_RE.match(cleaned)
    if match is not None:
        month = MONTHS[match["month"]]
        year = int(match["year"])
        return (
            match["place"].strip(),
            date(year, month, int(match["first"])),
            date(year, month, int(match["second"])),
        )
    match = _CROSS_MONTH_RE.match(cleaned)
    if match is not None:
        year = int(match["year"])
        return (
            match["place"].strip(),
            date(year, MONTHS[match["first_month"]], int(match["first"])),
            date(year, MONTHS[match["second_month"]], int(match["second"])),
        )
    match = _SINGLE_DAY_RE.match(cleaned)
    if match is not None:
        start = date(int(match["year"]), MONTHS[match["month"]], int(match["day"]))
        return match["place"].strip(), start, None
    return None


def parse_meeting_index(page_html: str) -> list[MeetingInfo]:
    """Parse the meeting index page of a study group.

    Args:
        page_html: The HTML of the meeting index page.

    Returns:
        The meetings found, in the order of the page.
    """
    tree = html.fromstring(page_html)
    meetings: list[MeetingInfo] = []
    for link in tree.xpath("//a[starts-with(@href, '/md/meeting.asp')]"):
        match = _MEETING_LINK_RE.search(link.get("href") or "")
        if match is None:
            continue
        parsed = _parse_meeting_text(link.text_content())
        if parsed is None:
            continue
        place, start_date, end_date = parsed
        try:
            meeting = MeetingId.from_code(match["code"])
        except ValueError:
            continue
        meetings.append(MeetingInfo(meeting, place, start_date, end_date))
    return meetings


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
