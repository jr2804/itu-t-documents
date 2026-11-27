"""Tests for the SQLite metadata store."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlmodel import select

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocType, Role
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.tables import DocumentQuestionRow, DocumentRow, DocumentSourceRow, PersonRow, QuestionRow

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def test_store_and_read_a_document(store: MetadataStore) -> None:
    """A stored document can be found again."""
    store.store_document(_document(192, DocType.CONTRIBUTION))

    with store.session() as session:
        records = session.exec(select(DocumentRow)).all()

    assert len(records) == 1
    assert records[0].document_id == "T25-SG12-C-0192"


def test_storing_a_document_twice_updates_it(store: MetadataStore) -> None:
    """Storing the same document again does not duplicate it."""
    store.store_document(_document(192, DocType.CONTRIBUTION, title="First"))
    store.store_document(_document(192, DocType.CONTRIBUTION, title="Second"))

    assert store.count_documents() == 1
    with store.session() as session:
        records = session.exec(select(DocumentRow)).all()

    assert records[0].title == "Second"


def test_store_question_and_people(store: MetadataStore) -> None:
    """A question and its people are stored."""
    question = Question(
        number=5,
        study_group=12,
        title="Telephonometric methodologies",
        working_group=WorkingGroup.parse("WP1/12"),
        people=[Person(name="Lars Birger NIELSEN", role=Role.RAPPORTEUR, organization="HBK A/S", country="Denmark")],
    )

    store.store_question(question, PERIOD.label)

    with store.session() as session:
        rows = session.exec(select(QuestionRow)).all()
        people = session.exec(select(PersonRow)).all()

    assert len(rows) == 1
    assert rows[0].working_group == "WP1/12"
    assert rows[0].title == "Telephonometric methodologies"
    assert len(people) == 1
    assert people[0].name == "Lars Birger NIELSEN"
    assert people[0].role == Role.RAPPORTEUR.value


def test_store_detail_keeps_what_the_listing_told(store: MetadataStore) -> None:
    """The detail page of a known document adds its title and keeps the rest."""
    meeting = MeetingId.from_code("260609")
    store.store_document(_document(192, DocType.CONTRIBUTION, posted=date(2026, 6, 9), meeting=meeting, sources=["Acme Corp", "Acme Europe"]))
    detail = DocumentMetadata(
        ref=DocumentRef.parse("T25-SG12-C-0192"), title="Title of the detail page", detail_url="https://www.itu.int/md/T25-SG12-C-0192/en"
    )

    row = store.store_detail(detail)

    assert row.title == "Title of the detail page"
    assert row.posted == date(2026, 6, 9)
    assert row.meeting_id is not None
    with store.session() as session:
        assert [source.source for source in session.exec(select(DocumentSourceRow).where(DocumentSourceRow.document_id == row.id))] == [
            "Acme Corp",
            "Acme Europe",
        ]
        linked = session.exec(select(DocumentQuestionRow).where(DocumentQuestionRow.document_id == row.id)).all()
        questions = [session.get(QuestionRow, link.question_id) for link in linked]
    assert [question.number for question in questions if question is not None] == [5]


def test_store_detail_of_an_unknown_document(store: MetadataStore) -> None:
    """A document that no listing told of is stored as its detail page describes it."""
    detail = DocumentMetadata(
        ref=DocumentRef.parse("T25-SG12-C-0007"), title="Known from its detail page", detail_url="https://www.itu.int/md/T25-SG12-C-0007/en"
    )

    store.store_detail(detail)

    with store.session() as session:
        rows = session.exec(select(DocumentRow)).all()
    assert [(row.document_id, row.title, row.posted, row.meeting_id) for row in rows] == [("T25-SG12-C-0007", "Known from its detail page", None, None)]


def test_store_detail_without_a_title_keeps_the_title(store: MetadataStore) -> None:
    """A detail page that tells no title does not blank the one of the listing."""
    store.store_document(_document(192, DocType.CONTRIBUTION, title="Title of the listing"))

    store.store_detail(DocumentMetadata(ref=DocumentRef.parse("T25-SG12-C-0192")))

    with store.session() as session:
        rows = session.exec(select(DocumentRow)).all()
    assert [row.title for row in rows] == ["Title of the listing"]


def _document(number: int, doc_type: DocType, **kwargs) -> DocumentMetadata:
    """Build document metadata for the store."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=doc_type,
        number=number,
        subtype=kwargs.get("subtype"),
        meeting=kwargs.get("meeting"),
    )
    return DocumentMetadata(
        ref=ref,
        title=kwargs.get("title", f"Document {number}"),
        sources=kwargs.get("sources", ["Acme Ltd. (Germany)"]),
        questions=kwargs.get("questions", [5]),
        posted=kwargs.get("posted", date(2026, 5, 27)),
        detail_url=f"https://www.itu.int/md/meetingdoc.asp?lang=en&parent={ref.document_id}",
    )


def test_close_releases_the_database_connections(tmp_path: Path, pooled_connections: Callable[[MetadataStore], int]) -> None:
    """Closing the store releases the connections it pooled."""
    store = MetadataStore(_settings(tmp_path))
    with store.session() as session:
        session.exec(select(DocumentRow)).all()
    assert pooled_connections(store) == 1

    store.close()

    assert pooled_connections(store) == 0


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MetadataStore]:
    """Return a metadata store in an isolated cache directory."""
    store = MetadataStore(_settings(tmp_path))
    yield store
    store.close()


def _settings(tmp_path: Path) -> Settings:
    """Return settings pointing at an isolated cache directory."""
    return Settings(cache_dir=tmp_path)
