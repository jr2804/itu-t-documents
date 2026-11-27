"""Read the header and the sibling meetings of a meeting document page."""

from __future__ import annotations

import re
from datetime import date

from itu_t_documents.models.documents import MeetingId
from itu_t_documents.models.metadata import MeetingHeader
from itu_t_documents.scraping.pages import clean_text as _clean
from itu_t_documents.scraping.pages import parse_page, scraping_error


def parse_other_meetings(page_html: str) -> list[MeetingId]:
    """Extract the sibling meetings listed on a meeting document page.

    The ITU-T pages carry an "Other Meetings" block that links to the other
    meetings of the study group. The meeting the page belongs to is shown as
    plain text and therefore not part of the result.

    Args:
        page_html: The HTML of the page.

    Returns:
        The meetings found, ordered as on the page.
    """
    tree = parse_page(page_html)
    if tree is None:
        raise scraping_error("other meetings", page_html)
    meetings: list[MeetingId] = []
    for cell in tree.xpath("//td[contains(., 'Other Meetings')]"):
        for link in cell.xpath(".//a"):
            label = _clean(link.text_content())
            # The block also links to document lists and language tools. Only
            # the date-labelled links name meetings.
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
                continue
            link_html = f"{label} {link.get('href') or ''}"
            match = re.search(r"parent=T\d{2}-SG\d{1,3}-(\d{6})-", link.get("href") or "")
            if match is None:
                raise scraping_error("other meetings link", link_html)
            try:
                meeting = MeetingId.from_code(match.group(1))
            except ValueError as error:
                raise scraping_error("other meetings link", link_html) from error
            if meeting not in meetings:
                meetings.append(meeting)
    return meetings


def parse_meeting_header(page_html: str) -> MeetingHeader:
    """Extract the descriptive header of a meeting document page.

    The header names the study period and the date range and place of the
    meeting. Entries the page does not carry are left as ``None``.

    Args:
        page_html: The HTML of the page.

    Returns:
        The values found in the header.

    Raises:
        ScrapingError: When the page cannot be read.
    """
    tree = parse_page(page_html)
    if tree is None:
        raise scraping_error("meeting header", page_html)
    text = _clean(tree.text_content())

    period = re.search(r"Study Period (\d{4})", text)
    dates = re.search(r"Meeting\s+from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", text)
    place = re.search(r"held in ([^\n]+?)\s+Other Meetings", text)
    return MeetingHeader(
        study_period=period.group(1) if period is not None else None,
        start_date=date.fromisoformat(dates.group(1)) if dates is not None else None,
        end_date=date.fromisoformat(dates.group(2)) if dates is not None else None,
        place=place.group(1).strip() if place is not None else None,
    )
