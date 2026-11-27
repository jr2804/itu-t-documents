"""The read models of the metadata store and how a row becomes one."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from itu_t_documents.models.enums import DocType
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
