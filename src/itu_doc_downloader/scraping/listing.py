"""Parser for the ITU-T meeting document listing pages.

The listing pages (``meetingdoc.asp?parent=…``) contain one table row per
document with the columns *number*, *title*, *source*, *questions* and *date*.
"""

from __future__ import annotations

import re
from datetime import date

from lxml.html import HtmlElement

from itu_doc_downloader.models.documents import DocumentMetadata, DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType
from itu_doc_downloader.scraping.pages import parse_page

#: Pattern of the question filter links, e.g. ``…&question=Q5/12``.
_QUESTION_RE = re.compile(r"question=(?P<number>Q\d+)/(?P<group>\d+)", re.IGNORECASE)

#: Pattern of the revision marker inside the number cell, e.g. ``(Rev.1)``.
_REVISION_RE = re.compile(r"Rev\.?\s*(?P<revision>\d+)", re.IGNORECASE)

#: Pattern of the number cell, e.g. ``[ 520-GEN ]``.
_NUMBER_RE = re.compile(r"\[(?P<number>[^\]]+)\]")

#: Pattern of the ``parent`` parameter of the link to the listing of a
#: temporary document sub-type.
_SUBTYPE_RE = re.compile(r"T\d{2}-SG\d{1,3}-(?P<meeting>\d{6})-TD-(?P<subtype>[A-Z0-9]+)")


def _clean(text: str) -> str:
    """Normalise whitespace of a scraped text fragment."""
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(text: str) -> date | None:
    """Parse an ISO date as used by the listing pages."""
    text = _clean(text)
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_listing(
    page_html: str,
    study_period: StudyPeriod,
    study_group: int,
    doc_type: DocType,
    meeting: MeetingId | None = None,
) -> list[DocumentMetadata]:
    """Parse a document listing page.

    Args:
        page_html: The HTML of the listing page.
        study_period: The study period the listing belongs to.
        study_group: The study group the listing belongs to.
        doc_type: The document type of the listing.
        meeting: The meeting the listing belongs to.

    Returns:
        The metadata of every document found on the page.
    """
    tree = parse_page(page_html)
    if tree is None:
        return []
    documents: list[DocumentMetadata] = []
    for row in tree.xpath("//tr[count(td) > 3][.//input[@name='chkFile']]"):
        document = _parse_row(row, study_period, study_group, doc_type, meeting)
        if document is not None:
            documents.append(document)
    return documents


def _parse_row(
    row: HtmlElement,
    study_period: StudyPeriod,
    study_group: int,
    doc_type: DocType,
    meeting: MeetingId | None,
) -> DocumentMetadata | None:
    """Parse a single listing row into document metadata."""
    checkbox = row.xpath(".//input[@name='chkFile']")[0]
    document_id = checkbox.get("id")
    if not document_id:
        return None

    try:
        ref = DocumentRef.parse(document_id)
    except ValueError:
        return None
    if ref.meeting is None and meeting is not None:
        ref = ref.model_copy(update={"meeting": meeting})

    cells = row.xpath("./td")
    number_text = _clean(cells[1].text_content()) if len(cells) > 1 else ""
    title = _clean(cells[2].text_content()) if len(cells) > 2 else ""
    source_names: list[str] = []
    if len(cells) > 3:
        source_names = [_clean(link.text_content()) for link in cells[3].xpath(".//a")]
    questions = _parse_questions(cells[4]) if len(cells) > 4 else []
    posted = _parse_date(cells[5].text_content()) if len(cells) > 5 else None

    revision: int | None = None
    revision_match = _REVISION_RE.search(number_text)
    if revision_match is not None:
        revision = int(revision_match["revision"])

    return DocumentMetadata(
        ref=ref,
        title=title,
        sources=source_names,
        questions=questions,
        posted=posted,
        revision=revision,
        detail_url=f"https://www.itu.int/md/meetingdoc.asp?lang=en&parent={document_id}",
    )


def _parse_questions(cell: HtmlElement) -> list[int]:
    """Extract the question numbers linked in the question column."""
    numbers: list[int] = []
    for link in cell.xpath(".//a"):
        match = _QUESTION_RE.search(link.get("href") or "")
        if match is None:
            continue
        number = int(match["number"].lstrip("Qq"))
        if number not in numbers:
            numbers.append(number)
    return numbers


def parse_subtypes(page_html: str, meeting: MeetingId) -> list[str]:
    """Return the temporary document sub-types a listing page offers.

    The aggregate listing of the temporary documents of a meeting only shows
    a preview of five documents per sub-type, so the full listing has to be
    fetched per sub-type.

    Args:
        page_html: The HTML of the listing page.
        meeting: The meeting whose sub-types are looked for. The pages link
            to the sub-types of the other meetings as well.

    Returns:
        The sub-type names, in the order of the page.
    """
    tree = parse_page(page_html)
    if tree is None:
        return []
    subtypes: list[str] = []
    for link in tree.xpath("//a[contains(@href, 'parent=')]"):
        href = link.get("href") or ""
        parent = href.split("parent=", maxsplit=1)[-1].split("&", maxsplit=1)[0]
        match = _SUBTYPE_RE.fullmatch(parent)
        if match is None or match["meeting"] != meeting.code:
            continue
        subtype = match["subtype"]
        if subtype not in subtypes:
            subtypes.append(subtype)
    return subtypes


def parse_total_items(page_html: str) -> int | None:
    """Return the number of items the listing reports, if present.

    Args:
        page_html: The HTML of the listing page.

    Returns:
        The total item count, or ``None`` when the page does not report it.
    """
    match = re.search(r"Results:\s*(?:<[^>]+>\s*)*(\d+)", page_html)
    if match is None:
        match = re.search(r"Results:\s*(\d+)", re.sub(r"<[^>]+>", "", page_html))
    return int(match.group(1)) if match is not None else None


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
        return []
    meetings: list[MeetingId] = []
    for cell in tree.xpath("//td[contains(., 'Other Meetings')]"):
        for link in cell.xpath(".//a"):
            match = re.search(r"parent=T\d{2}-SG\d{1,3}-(\d{6})-", link.get("href") or "")
            if match is None:
                continue
            try:
                meeting = MeetingId.from_code(match.group(1))
            except ValueError:
                continue
            if meeting not in meetings:
                meetings.append(meeting)
    return meetings


def parse_meeting_header(page_html: str) -> dict[str, str]:
    """Extract the descriptive header of a meeting document page.

    The header names the study group, the study period and the date range and
    place of the meeting.

    Args:
        page_html: The HTML of the page.

    Returns:
        The found values, with missing entries left out.
    """
    tree = parse_page(page_html)
    if tree is None:
        return {}
    header: dict[str, str] = {}
    text = _clean(tree.text_content())

    period = re.search(r"Study Period (\d{4})", text)
    if period is not None:
        header["study_period"] = period.group(1)

    dates = re.search(r"Meeting\s+from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", text)
    if dates is not None:
        header["start_date"] = dates.group(1)
        header["end_date"] = dates.group(2)

    place = re.search(r"held in ([^\n]+?)\s+Other Meetings", text)
    if place is not None:
        header["place"] = place.group(1).strip()
    return header
