"""Scrapers for the ITU-T meeting document pages."""

from __future__ import annotations

from itu_t_documents.scraping.detail import parse_files, parse_title
from itu_t_documents.scraping.listing import parse_listing, parse_other_meetings
from itu_t_documents.scraping.meetings import parse_meeting_index
from itu_t_documents.scraping.questions import parse_questions

__all__ = [
    "parse_files",
    "parse_listing",
    "parse_meeting_index",
    "parse_other_meetings",
    "parse_questions",
    "parse_title",
]
