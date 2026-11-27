"""Tests for the parsers that read a page of the ITU-T."""

from __future__ import annotations

import pytest

from itu_t_documents.errors import ScrapingError
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping import detail, listing, meetings, questions

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


@pytest.mark.parametrize(
    "parse",
    [
        pytest.param(lambda: listing.parse_listing("", PERIOD, 12, DocType.CONTRIBUTION), id="listing"),
        pytest.param(lambda: listing.parse_meeting_header(""), id="meeting-header"),
        pytest.param(lambda: listing.parse_other_meetings(""), id="other-meetings"),
        pytest.param(lambda: meetings.parse_meeting_index(""), id="meeting-index"),
        pytest.param(lambda: questions.parse_questions("", 12), id="questions"),
        pytest.param(lambda: detail.parse_files(""), id="files"),
        pytest.param(lambda: detail.parse_title(""), id="title"),
    ],
)
def test_parsers_refuse_an_empty_page(parse) -> None:
    """An empty answer is visible, never a plausible empty result."""
    with pytest.raises(ScrapingError):
        parse()
