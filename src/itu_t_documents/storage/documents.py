"""Write a document and what belongs to it into the metadata store.

A listing tells other things about a document than its detail page, so
there is a writer for each. Both see to it that the rows a document refers
to — the study period, the study group, the meeting and the questions —
exist, and neither erases what the other told.
"""

from __future__ import annotations

from sqlmodel import Session, select

from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.storage.tables import (
    DocumentFileRow,
    DocumentQuestionRow,
    DocumentRow,
    DocumentSourceRow,
    MeetingRow,
    QuestionRow,
    StudyGroupRow,
    StudyPeriodRow,
    row_id,
)


def write_document(session: Session, metadata: DocumentMetadata) -> DocumentRow:
    """Insert or update a document and its links.

    Args:
        session: The database session to write in; it is committed here.
        metadata: The metadata of the document, as a listing tells it.

    Returns:
        The stored row.
    """
    ref = metadata.ref
    group = ensure_group(session, ref)
    document = ensure_document(session, metadata, group)
    link_sources(session, document, metadata.sources)
    link_questions(session, document, group, metadata.questions)
    link_files(session, document, metadata)
    session.commit()
    session.refresh(document)
    return document


def write_detail(session: Session, detail: DocumentMetadata) -> DocumentRow:
    """Store what the detail page of a document says.

    The detail page gives the title and the renditions of a document. What
    a listing said — the posting date, the revision, the sources, the
    questions and the meeting — is unknown to it, so that is kept. A
    document that no listing told of yet is stored as its detail page
    describes it.

    Args:
        session: The database session to write in; it is committed here.
        detail: The metadata read from the detail page of the document.

    Returns:
        The stored row.
    """
    ref = detail.ref
    document = session.exec(select(DocumentRow).where(DocumentRow.document_id == ref.document_id)).first()
    if document is None:
        document = ensure_document(session, detail, ensure_group(session, ref))
    document.title = detail.title or document.title
    document.detail_url = detail.detail_url or document.detail_url
    link_files(session, document, detail)
    session.commit()
    session.refresh(document)
    return document


def ensure_group(session: Session, ref: DocumentRef) -> StudyGroupRow:
    """Return the study group row of a document, creating it when needed.

    The study period row the group refers to is created when needed as well.
    """
    label = ref.study_period.label
    period = session.exec(select(StudyPeriodRow).where(StudyPeriodRow.label == label)).first()
    if period is None:
        session.add(
            StudyPeriodRow(
                label=label,
                start_year=ref.study_period.start_year,
                end_year=ref.study_period.end_year,
            )
        )
    group = session.exec(
        select(StudyGroupRow).where(
            StudyGroupRow.period_label == label,
            StudyGroupRow.number == ref.study_group,
        )
    ).first()
    if group is None:
        group = StudyGroupRow(period_label=label, number=ref.study_group)
        session.add(group)
        session.flush()
    return group


def ensure_document(session: Session, metadata: DocumentMetadata, group: StudyGroupRow) -> DocumentRow:
    """Return the document row of the metadata, creating it when needed.

    The row is filled with what the metadata tells; it does not commit.
    """
    ref = metadata.ref
    document = session.exec(select(DocumentRow).where(DocumentRow.document_id == ref.document_id)).first()
    if document is None:
        document = DocumentRow(
            document_id=ref.document_id,
            study_group_id=row_id(group),
            doc_type=ref.doc_type.value,
            number=ref.number,
        )
        session.add(document)
    document.meeting_id = ensure_meeting(session, group, ref)
    document.doc_type = ref.doc_type.value
    document.number = ref.number
    document.subtype = ref.subtype
    document.title = metadata.title
    document.posted = metadata.posted
    document.revision = metadata.revision
    document.detail_url = metadata.detail_url
    session.add(document)
    session.flush()
    return document


def ensure_meeting(session: Session, group: StudyGroupRow, ref: DocumentRef) -> int | None:
    """Return the id of the meeting row of a document, creating it when needed.

    Returns:
        The id of the meeting row, or ``None`` when the document was not
        posted to a meeting.
    """
    if ref.meeting is None:
        return None
    meeting = session.exec(
        select(MeetingRow).where(
            MeetingRow.study_group_id == group.id,
            MeetingRow.code == ref.meeting.code,
        )
    ).first()
    if meeting is None:
        meeting = MeetingRow(
            study_group_id=row_id(group),
            code=ref.meeting.code,
            start_date=ref.meeting.start_date,
            end_date=ref.meeting.end_date,
        )
        session.add(meeting)
        session.flush()
    return row_id(meeting)


def link_sources(session: Session, document: DocumentRow, sources: list[str]) -> None:
    """Link the submitting organisations to a document."""
    for source in sources:
        existing = session.exec(
            select(DocumentSourceRow).where(
                DocumentSourceRow.document_id == document.id,
                DocumentSourceRow.source == source,
            )
        ).first()
        if existing is None:
            session.add(DocumentSourceRow(document_id=row_id(document), source=source))


def link_questions(session: Session, document: DocumentRow, group: StudyGroupRow, questions: list[int]) -> None:
    """Link the questions a document was handled in."""
    for number in questions:
        question = session.exec(
            select(QuestionRow).where(
                QuestionRow.study_group_id == group.id,
                QuestionRow.number == number,
            )
        ).first()
        if question is None:
            question = QuestionRow(study_group_id=row_id(group), number=number)
            session.add(question)
            session.flush()
        link = session.exec(
            select(DocumentQuestionRow).where(
                DocumentQuestionRow.document_id == document.id,
                DocumentQuestionRow.question_id == question.id,
            )
        ).first()
        if link is None:
            session.add(DocumentQuestionRow(document_id=row_id(document), question_id=row_id(question)))


def link_files(session: Session, document: DocumentRow, metadata: DocumentMetadata) -> None:
    """Link the available renditions to a document."""
    for file in metadata.files:
        existing = session.exec(
            select(DocumentFileRow).where(
                DocumentFileRow.document_id == document.id,
                DocumentFileRow.format_code == file.format_code,
                DocumentFileRow.language_code == file.language_code,
            )
        ).first()
        if existing is None:
            existing = DocumentFileRow(
                document_id=row_id(document),
                format_code=file.format_code,
                language_code=file.language_code,
                url=file.url,
            )
            session.add(existing)
        existing.language_code = file.language_code
        existing.size_bytes = file.size_bytes
        existing.posted = file.posted
        existing.url = file.url
