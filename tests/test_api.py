"""Tests for the high level API."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_doc_downloader.api import IncompleteListingError, ItuDocuments
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType
from tests.fakes import DOCUMENT_BYTES, FakeClient


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


def test_fetch_documents_reads_every_subtype(api: ItuDocuments, fake_client: FakeClient) -> None:
    """The temporary documents of a meeting are read per sub-type."""
    documents = api.fetch_documents(
        12,
        DocType.TEMPORARY_DOCUMENT,
        StudyPeriod(start_year=2025, end_year=2028),
        MeetingId.from_code("261015"),
    )

    assert documents
    assert "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN" in fake_client.requested
    assert "T25-SG12-261015-TD-GEN-0523" in {document.document_id for document in documents}


def test_fetch_documents_without_a_subtype(api: ItuDocuments, fake_client: FakeClient) -> None:
    """A listing that offers no sub-type is read as it is."""
    documents = api.fetch_documents(
        12,
        DocType.TEMPORARY_DOCUMENT,
        StudyPeriod(start_year=2025, end_year=2028),
        MeetingId.from_code("250114"),
    )

    assert documents
    assert not any(url.endswith("-TD-GEN") for url in fake_client.requested)


def test_fetch_documents_of_a_truncated_listing(api: ItuDocuments) -> None:
    """A listing that holds fewer documents than it reports is refused."""
    with pytest.raises(IncompleteListingError):
        api.fetch_documents(
            12,
            DocType.CONTRIBUTION,
            StudyPeriod(start_year=2025, end_year=2028),
            MeetingId.from_code("270119"),
        )


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


def test_download_a_revised_document(api: ItuDocuments) -> None:
    """The original of a revised document is downloaded."""
    ref = DocumentRef.parse("T25-SG02-C-0001")

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.name == "MSW-E.docx"
    assert path.read_bytes() == DOCUMENT_BYTES


def test_download_a_document_that_was_only_revised(api: ItuDocuments) -> None:
    """A revision is downloaded when the original is gone."""
    ref = DocumentRef.parse("T25-SG02-C-0002")

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.name == "MSW-E-R1.docx"
    assert path.read_bytes() == DOCUMENT_BYTES
