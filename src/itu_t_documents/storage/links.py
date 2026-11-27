"""Link the rows a document refers to in the metadata store."""

from __future__ import annotations

from sqlmodel import Session, select

from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.storage.tables import (
    DocumentFileRow,
    DocumentQuestionRow,
    DocumentRow,
    DocumentSourceRow,
    QuestionRow,
    StudyGroupRow,
    row_id,
)


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
                DocumentFileRow.revision == file.revision,
            )
        ).first()
        if existing is None:
            existing = DocumentFileRow(
                document_id=row_id(document),
                format_code=file.format_code,
                language_code=file.language_code,
                url=file.url,
                revision=file.revision,
            )
            session.add(existing)
        existing.size_bytes = file.size_bytes
        existing.posted = file.posted
        existing.url = file.url
