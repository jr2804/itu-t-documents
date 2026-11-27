"""Parse the document rows of an ITU-T document listing page."""

from __future__ import annotations

import re
from datetime import date

from lxml.html import HtmlElement

from itu_t_documents.models.documents import DocumentRef, MeetingId, detail_url
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping.pages import clean_text as _clean
from itu_t_documents.scraping.pages import parse_page, scraping_error

#: Pattern of the question filter links, e.g. ``…&question=Q5/12``.
_QUESTION_RE = re.compile(r"question=(?P<number>Q\d+)/(?P<group>\d+)", re.IGNORECASE)

#: Pattern of the revision marker inside the number cell, e.g. ``(Rev.1)``.
_REVISION_RE = re.compile(r"Rev\.?\s*(?P<revision>\d+)", re.IGNORECASE)


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

    Raises:
        ScrapingError: When the page is not a document listing or a row
            carries an identifier that cannot be parsed.
    """
    tree = parse_page(page_html)
    rows = tree.xpath("//tr[count(td) > 3][.//input[@name='chkFile']]") if tree is not None else []
    if not rows and (tree is None or not tree.xpath("//input[@name='chkFile']")):
        raise scraping_error("document listing", page_html)
    return [
        _parse_row(row, study_period, study_group, doc_type, meeting)
        for row in rows
    ]


def _parse_row(
    row: HtmlElement,
    study_period: StudyPeriod,
    study_group: int,
    doc_type: DocType,
    meeting: MeetingId | None,
) -> DocumentMetadata:
    """Parse a single listing row into document metadata.

    Raises:
        ScrapingError: When the identifier of the row cannot be read.
    """
    checkbox = row.xpath(".//input[@name='chkFile']")[0]
    document_id = checkbox.get("id")
    row_text = _clean(row.text_content())
    if not document_id:
        raise scraping_error("document listing row", row_text)

    try:
        ref = DocumentRef.parse(document_id)
    except ValueError as error:
        raise scraping_error("document listing row", row_text) from error
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
        detail_url=detail_url(document_id),
    )


def _parse_date(text: str) -> date | None:
    """Parse an ISO date as used by the listing pages."""
    text = _clean(text)
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


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
