"""Tests for the high level API."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_doc_downloader.api import ItuDocuments
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType
from tests.fakes import FakeClient


@pytest.fixture
def api(tmp_path: Path, fake_client: FakeClient) -> ItuDocuments:
    """Return an API backed by the recorded fixtures."""
    return ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)


def test_list_meetings(api: ItuDocuments) -> None:
    """The API lists the meetings of a study group."""
    found = api.list_meetings(12, StudyPeriod(start_year=2025, end_year=2028))

    assert [meeting.code for meeting in found][:3] == ["270119", "261015", "260609"]


def test_list_questions(api: ItuDocuments) -> None:
    """The API lists the questions under study of a study group."""
    found = api.list_questions(12, StudyPeriod(start_year=2025, end_year=2028))

    assert [question.code for question in found][:3] == ["Q1/12", "Q2/12", "Q4/12"]
    assert found[0].working_group.code == "PLEN"


def test_sync_meeting_stores_the_documents(api: ItuDocuments) -> None:
    """Syncing a meeting stores the documents of the meeting."""
    stored = api.sync_meeting(
        12,
        MeetingId.from_code("260609"),
        StudyPeriod(start_year=2025, end_year=2028),
        (DocType.CONTRIBUTION,),
    )

    assert stored == 3
    assert api.store.count_documents() == 3


def test_find_documents_by_question(api: ItuDocuments) -> None:
    """The stored documents can be searched by question."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    records = api.documents_for_question(study_group=12, question=7)

    assert len(records) == 1
    assert records[0].document_id == "T25-SG12-C-0192"
    assert records[0].sources == ("Technische Universität Berlin (TU Berlin) (Germany)",)
    assert records[0].meeting_code == "260609"


def test_find_documents_by_source(api: ItuDocuments) -> None:
    """The stored documents can be searched by source."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    records = api.contributions_by_source(study_group=12, source="Hottinger")

    assert len(records) == 1
    assert records[0].number == 191
    assert records[0].sources == ("Hottinger Brüel & Kjaer A/S (Denmark)",)


def test_top_sources(api: ItuDocuments) -> None:
    """The sources are counted by the number of submitted documents."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    counts = api.top_sources(study_group=12, meetings=("260609",))

    assert counts
    assert {count.source for count in counts} == {
        "Technische Universität Berlin (TU Berlin) (Germany)",
        "Hottinger Brüel & Kjaer A/S (Denmark)",
        "Zambia Information & Communications Technology Authority (ZICTA) (Zambia)",
    }
    assert all(count.contributions == 1 for count in counts)
    assert all(count.temporary_documents == 0 for count in counts)
    assert all(count.meetings == ("260609",) for count in counts)
