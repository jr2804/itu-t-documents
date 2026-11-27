"""Ask the metadata store what was seen.

The functions read the local database only; the network is not contacted.
:class:`DocumentRecord` is a stored document with the sources and the
questions it is linked to, :class:`SourceCount` the result of a count per
source.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from itu_t_documents.models.enums import DocType
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.tables import (
    DocumentQuestionRow,
    DocumentRow,
    DocumentSourceRow,
    MeetingRow,
    QuestionRow,
    StudyGroupRow,
)


@dataclass(frozen=True)
class DocumentRecord:
    """A document as stored in the metadata database."""

    document_id: str
    doc_type: DocType
    number: int
    subtype: str | None
    title: str
    sources: tuple[str, ...] = ()
    questions: tuple[int, ...] = ()
    posted: date | None = None
    revision: int | None = None
    study_group: int = 0
    study_period: str = ""
    meeting_code: str | None = None
    detail_url: str = ""


@dataclass(frozen=True)
class SourceCount:
    """The number of documents a single source submitted."""

    source: str
    count: int
    contributions: int = 0
    temporary_documents: int = 0
    meetings: tuple[str, ...] = ()


def find_documents(
    store: MetadataStore,
    *,
    study_group: int | None = None,
    study_period: str | None = None,
    doc_type: DocType | None = None,
    doc_types: tuple[DocType, ...] | None = None,
    meeting: str | None = None,
    question: int | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> list[DocumentRecord]:
    """Search the stored documents.

    Args:
        store: The metadata store to search.
        study_group: Restrict to a study group.
        study_period: Restrict to a study period, e.g. ``2025-2028``.
        doc_type: Restrict to a single document type.
        doc_types: Restrict to several document types.
        meeting: Restrict to a meeting, given by its DMS code, e.g. ``270119``.
        question: Restrict to the documents handled in a question.
        source: Restrict to the documents submitted by a source; the match
            is case insensitive and partial.
        limit: Maximum number of results.

    Returns:
        The matching documents, newest number first.
    """
    with store.session() as session:
        statement = select(DocumentRow)
        if study_group is not None or study_period is not None:
            statement = statement.join(StudyGroupRow)
        if study_group is not None:
            statement = statement.where(StudyGroupRow.number == study_group)
        if study_period is not None:
            statement = statement.where(StudyGroupRow.period_label == study_period)
        if doc_type is not None:
            statement = statement.where(DocumentRow.doc_type == doc_type.value)
        if doc_types is not None:
            # SQLModel declares its table columns with plain Python types, so the
            # SQLAlchemy helpers on the columns are invisible to the type checker.
            values = [doc_type.value for doc_type in doc_types]
            statement = statement.where(DocumentRow.doc_type.in_(values))  # ty: ignore[missing-attribute]
        if meeting is not None:
            statement = statement.join(MeetingRow).where(MeetingRow.code == meeting)
        if question is not None:
            statement = statement.join(DocumentQuestionRow).join(QuestionRow).where(QuestionRow.number == question)
        if source is not None:
            # A document is returned once, however many of its sources
            # match, so the sources are matched in a subquery and not in a
            # join.
            submitted_by = select(DocumentSourceRow.document_id).where(DocumentSourceRow.source.ilike(f"%{source}%"))  # ty: ignore[missing-attribute]
            statement = statement.where(DocumentRow.id.in_(submitted_by))  # ty: ignore[missing-attribute]
        statement = statement.order_by(DocumentRow.number.desc())  # ty: ignore[missing-attribute]
        if limit is not None:
            statement = statement.limit(limit)

        rows = session.exec(statement).all()
        return [to_record(session, row) for row in rows]


def top_sources(
    store: MetadataStore,
    study_group: int,
    meetings: tuple[str, ...] | None = None,
    doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
    limit: int = 10,
) -> list[SourceCount]:
    """Count the documents every source submitted.

    Args:
        store: The metadata store to search.
        study_group: The study group number.
        meetings: The DMS codes of the meetings to consider. Defaults to
            every stored meeting of the study group.
        doc_types: The document types to count.
        limit: The maximum number of sources to report.

    Returns:
        The sources with their document counts, most prolific first.
    """
    with store.session() as session:
        statement = (
            select(DocumentRow)
            .join(DocumentSourceRow)
            .join(StudyGroupRow)
            .where(StudyGroupRow.number == study_group)
            .where(DocumentRow.doc_type.in_([doc_type.value for doc_type in doc_types]))  # ty: ignore[missing-attribute]
        )
        rows = session.exec(statement).all()
        records = [to_record(session, row) for row in rows]

    counts: dict[str, SourceCount] = {}
    for record in records:
        if meetings is not None and record.meeting_code not in meetings:
            continue
        for source in record.sources:
            current = counts.get(source)
            if current is None:
                current = SourceCount(source=source, count=0)
                counts[source] = current
            updated = SourceCount(
                source=current.source,
                count=current.count + 1,
                contributions=current.contributions + (1 if record.doc_type is DocType.CONTRIBUTION else 0),
                temporary_documents=current.temporary_documents + (1 if record.doc_type is DocType.TEMPORARY_DOCUMENT else 0),
                meetings=current.meetings + ((record.meeting_code,) if record.meeting_code and record.meeting_code not in current.meetings else ()),
            )
            counts[source] = updated

    ordered = sorted(counts.values(), key=lambda item: (-item.count, item.source))
    return ordered[:limit]


def to_record(session: Session, row: DocumentRow) -> DocumentRecord:
    """Build a :class:`DocumentRecord` from a database row.

    Args:
        session: The session to read the sources, the questions, the study
            group and the meeting of the document from.
        row: The row of the document.

    Returns:
        The record of the document.
    """
    sources = tuple(source.source for source in session.exec(select(DocumentSourceRow).where(DocumentSourceRow.document_id == row.id)).all())
    questions = tuple(
        question.number for question in session.exec(select(QuestionRow).join(DocumentQuestionRow).where(DocumentQuestionRow.document_id == row.id)).all()
    )
    group = session.get(StudyGroupRow, row.study_group_id)
    meeting_code = None
    if row.meeting_id is not None:
        meeting = session.get(MeetingRow, row.meeting_id)
        meeting_code = meeting.code if meeting is not None else None
    return DocumentRecord(
        document_id=row.document_id,
        doc_type=DocType(row.doc_type),
        number=row.number,
        subtype=row.subtype,
        title=row.title,
        sources=sources,
        questions=questions,
        posted=row.posted,
        revision=row.revision,
        study_group=group.number if group is not None else 0,
        study_period=group.period_label if group is not None else "",
        meeting_code=meeting_code,
        detail_url=row.detail_url,
    )
