"""Parser for the ITU-T meeting document listing pages.

The listing pages (``meetingdoc.asp?parent=…``) contain one table row per
document with the columns *number*, *title*, *source*, *questions* and *date*.
The parsers live in :mod:`listing_rows`, :mod:`listing_navigation` and
:mod:`meeting_page`; this module keeps their public names importable together.
"""

from __future__ import annotations

from datetime import date

from itu_t_documents.scraping.listing_navigation import parse_next_page, parse_subtypes, parse_total_items
from itu_t_documents.scraping.listing_rows import _parse_date as _parse_date_from_rows
from itu_t_documents.scraping.listing_rows import parse_listing
from itu_t_documents.scraping.meeting_page import parse_meeting_header, parse_other_meetings

__all__ = [
    "parse_listing",
    "parse_meeting_header",
    "parse_next_page",
    "parse_other_meetings",
    "parse_subtypes",
    "parse_total_items",
]


def _parse_date(text: str) -> date | None:
    """Parse an ISO date as used by the listing pages."""
    return _parse_date_from_rows(text)
