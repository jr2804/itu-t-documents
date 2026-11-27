"""Tests for the URL builders of the ITU-T web applications."""

from __future__ import annotations

import pytest

from itu_doc_downloader.models.documents import MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType
from itu_doc_downloader.urls import (
    PERIOD_INDICES,
    detail_url,
    listing_url,
    meeting_summary_url,
    period_index,
    questions_url,
    structure_url,
    study_group_page_url,
)

PERIOD = StudyPeriod(start_year=2025, end_year=2028)
MEETING = MeetingId.from_code("261015")


def test_period_index_of_the_current_period() -> None:
    """The current study period has a known index."""
    assert period_index(PERIOD) == 18
    assert PERIOD_INDICES["2025-2028"] == 18


def test_period_index_of_an_unknown_period() -> None:
    """A study period the ITU-T does not know cannot be constructed."""
    with pytest.raises(ValueError, match="1999-2002"):
        StudyPeriod(start_year=1999, end_year=2002)


def test_listing_url_of_a_meeting() -> None:
    """The listing of a meeting carries the meeting and the document type."""
    url = listing_url(PERIOD, 12, DocType.TEMPORARY_DOCUMENT, MEETING)

    assert url == "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD"


def test_listing_url_without_a_meeting() -> None:
    """The listing of a study period carries no meeting."""
    url = listing_url(PERIOD, 12, DocType.COLLECTIVE_LETTER)

    assert url == "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-COL"


def test_listing_url_of_a_subtype() -> None:
    """The listing of a sub-type carries the sub-type."""
    url = listing_url(PERIOD, 12, DocType.TEMPORARY_DOCUMENT, MEETING, "GEN")

    assert url == "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN"


def test_listing_url_of_a_single_digit_study_group() -> None:
    """A single digit study group is zero padded in the identifier."""
    url = listing_url(PERIOD, 5, DocType.CONTRIBUTION, MeetingId.from_code("260609"))

    assert url == "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG05-260609-C"


def test_study_group_page_url_of_a_single_digit_study_group() -> None:
    """A single digit study group is zero padded in the page path."""
    url = study_group_page_url(PERIOD, 5)

    assert url == "https://www.itu.int/en/ITU-T/studygroups/2025-2028/05/Pages/default.aspx"


def test_detail_url() -> None:
    """The detail page of a document is addressed by its identifier."""
    assert detail_url("T25-SG12-C-0192") == ("https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-C-0192")


def test_meeting_summary_url() -> None:
    """The summary page of a meeting is addressed by meeting and study group."""
    url = meeting_summary_url(PERIOD, 12, MEETING)

    assert url == "https://www.itu.int/md/T25-SG12-261015/sum/en"


def test_study_group_page_url() -> None:
    """The study group page is addressed by period and study group."""
    assert study_group_page_url(PERIOD, 12) == ("https://www.itu.int/en/ITU-T/studygroups/2025-2028/12/Pages/default.aspx")


def test_questions_and_structure_urls() -> None:
    """The questions and the structure page of a study group carry the period index."""
    assert questions_url(12, 18) == "https://www.itu.int/net4/ITU-T/lists/loqr.aspx?Group=12&Period=18"
    assert structure_url(12, 18) == "https://www.itu.int/net4/ITU-T/lists/sgstructure.aspx?Group=12&Period=18"
