"""Tests for the SQLite metadata store."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlmodel import select

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentMetadata, DocumentRef, StudyPeriod
from itu_t_documents.models.enums import DocType, Role
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.storage.database import DocumentRow, MetadataStore, PersonRow, QuestionRow

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def _settings(tmp_path: Path) -> Settings:
    """Return settings pointing at an isolated cache directory."""
    return Settings(cache_dir=tmp_path)


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


@pytest.fixture
def store(tmp_path: Path) -> MetadataStore:
    """Return a metadata store in an isolated cache directory."""
    return MetadataStore(_settings(tmp_path))


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
