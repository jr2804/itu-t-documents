"""Read the sub-types and the pagination of an ITU-T document listing."""

from __future__ import annotations

import re
from html import unescape

from itu_t_documents.models.documents import MeetingId
from itu_t_documents.scraping.pages import parse_page, scraping_error

#: Pattern of the ``parent`` parameter of the link to the listing of a
#: temporary document sub-type.
_SUBTYPE_RE = re.compile(r"T\d{2}-SG\d{1,3}-(?P<meeting>\d{6})-TD-(?P<subtype>[A-Z0-9]+)")

#: Pattern of the link to the next page of a listing, e.g.
#: ``<a href="/md/meetingdoc.asp?…&amp;PageLB=900"><strong>Next</strong>``.
_NEXT_PAGE_RE = re.compile(r'<a\s+href="(?P<href>[^"]+)"\s*>\s*<strong>\s*Next\s*</strong>', re.IGNORECASE)


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
        raise scraping_error("temporary document sub-types", page_html)
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


def parse_next_page(page_html: str) -> str | None:
    """Return the link to the next page of a listing, if the listing has one.

    A listing longer than the page size spans several pages. The page links to
    the next one until the last page, which has no such link.

    Args:
        page_html: The HTML of a page of the listing.

    Returns:
        The path of the next page, e.g.
        ``/md/meetingdoc.asp?lang=en&parent=T25-SG12-R&PageLB=900``, or
        ``None`` when the page is the last one.
    """
    match = _NEXT_PAGE_RE.search(page_html)
    return unescape(match["href"]) if match is not None else None
