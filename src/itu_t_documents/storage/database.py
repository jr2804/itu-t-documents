"""SQLite metadata store.

The store keeps the metadata of every document, meeting and question that has
been seen. It lives in the per-user cache directory, so a second run of the
tool answers questions without contacting the ITU-T web site again.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from sqlalchemy import create_engine
from sqlmodel import Field, Session, SQLModel, select

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentMetadata, DocumentRef
from itu_t_documents.models.questions import Question

#: Name of the SQLite database inside the cache directory.
DATABASE_FILE = "metadata.db"


class HasIdentifier(Protocol):
    """A row with a primary key."""

    @property
    def id(self) -> int | None: ...


def _row_id(row: HasIdentifier) -> int:
    """Return the primary key of a persisted row.

    Args:
        row: The row to read the primary key from.

    Returns:
        The primary key of the row.

    Raises:
        RuntimeError: When the row has not been persisted yet.
    """
    identifier = row.id
    if identifier is None:
        raise RuntimeError("the row has not been persisted yet")
    return identifier


class StudyPeriodRow(SQLModel, table=True):
    """An ITU-T study period."""

    __tablename__ = "study_period"

    label: str = Field(primary_key=True)
    start_year: int
    end_year: int


class StudyGroupRow(SQLModel, table=True):
    """An ITU-T study group within a study period."""

    __tablename__ = "study_group"

    id: int | None = Field(default=None, primary_key=True)
    period_label: str = Field(foreign_key="study_period.label")
    number: int
    title: str = ""


class MeetingRow(SQLModel, table=True):
    """A meeting of a study group."""

    __tablename__ = "meeting"

    id: int | None = Field(default=None, primary_key=True)
    study_group_id: int = Field(foreign_key="study_group.id")
    code: str = Field(index=True)
    start_date: date
    end_date: date | None = None
    place: str | None = None

    @property
    def unique_key(self) -> str:
        """A key that is unique across the whole store."""
        return f"{self.study_group_id}:{self.code}"


class QuestionRow(SQLModel, table=True):
    """A question under study of a study group."""

    __tablename__ = "question"

    id: int | None = Field(default=None, primary_key=True)
    study_group_id: int = Field(foreign_key="study_group.id")
    number: int
    title: str = ""
    working_group: str = ""


class PersonRow(SQLModel, table=True):
    """A person holding a role for a question under study."""

    __tablename__ = "person"

    id: int | None = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id")
    name: str
    role: str
    organization: str | None = None
    country: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None


class DocumentRow(SQLModel, table=True):
    """A meeting document."""

    __tablename__ = "document"

    id: int | None = Field(default=None, primary_key=True)
    document_id: str = Field(index=True, unique=True)
    study_group_id: int = Field(foreign_key="study_group.id")
    meeting_id: int | None = Field(default=None, foreign_key="meeting.id")
    doc_type: str
    number: int
    subtype: str | None = None
    title: str = ""
    posted: date | None = None
    revision: int | None = None
    detail_url: str = ""


class DocumentSourceRow(SQLModel, table=True):
    """An organisation that submitted a document."""

    __tablename__ = "document_source"

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    source: str


class DocumentQuestionRow(SQLModel, table=True):
    """The link between a document and a question it was handled in."""

    __tablename__ = "document_question"

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    question_id: int = Field(foreign_key="question.id")


class DocumentFileRow(SQLModel, table=True):
    """A downloadable rendition of a document."""

    __tablename__ = "document_file"

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    format_code: str
    language_code: str
    size_bytes: int | None = None
    posted: date | None = None
    url: str


class MetadataStore:
    """The SQLite metadata store of the ITU-T documents."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Open the store.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
        """
        self.settings = settings or Settings()
        self.cache_dir = self.settings.resolved_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / DATABASE_FILE
        self.engine = create_engine(f"sqlite:///{self.database_path}")
        SQLModel.metadata.create_all(self.engine)

    def session(self) -> Session:
        """Return a new database session."""
        return Session(self.engine)

    def store_document(self, metadata: DocumentMetadata) -> DocumentRow:
        """Insert or update a document and its links.

        Args:
            metadata: The metadata of the document.

        Returns:
            The stored row.
        """
        ref = metadata.ref
        with self.session() as session:
            group = MetadataStore._ensure_group(session, ref)
            document = MetadataStore._ensure_document(session, metadata, group)
            self._link_sources(session, document, metadata.sources)
            MetadataStore._link_questions(session, document, group, metadata.questions)
            self._link_files(session, document, metadata)
            session.commit()
            session.refresh(document)
            return document

    @staticmethod
    def _ensure_group(session: Session, ref: DocumentRef) -> StudyGroupRow:
        """Return the study group row of a document, creating it when needed."""
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

    @staticmethod
    def _ensure_meeting(session: Session, group: StudyGroupRow, ref: DocumentRef) -> int | None:
        """Return the id of the meeting row of a document, creating it when needed."""
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
                study_group_id=_row_id(group),
                code=ref.meeting.code,
                start_date=ref.meeting.start_date,
                end_date=ref.meeting.end_date,
            )
            session.add(meeting)
            session.flush()
        return _row_id(meeting)

    @staticmethod
    def _ensure_document(session: Session, metadata: DocumentMetadata, group: StudyGroupRow) -> DocumentRow:
        """Return the document row of the metadata, creating it when needed."""
        ref = metadata.ref
        document = session.exec(select(DocumentRow).where(DocumentRow.document_id == ref.document_id)).first()
        if document is None:
            document = DocumentRow(
                document_id=ref.document_id,
                study_group_id=_row_id(group),
                doc_type=ref.doc_type.value,
                number=ref.number,
            )
            session.add(document)
        document.meeting_id = MetadataStore._ensure_meeting(session, group, ref)
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

    @staticmethod
    def _link_sources(session: Session, document: DocumentRow, sources: list[str]) -> None:
        """Link the submitting organisations to a document."""
        for source in sources:
            existing = session.exec(
                select(DocumentSourceRow).where(
                    DocumentSourceRow.document_id == document.id,
                    DocumentSourceRow.source == source,
                )
            ).first()
            if existing is None:
                session.add(DocumentSourceRow(document_id=_row_id(document), source=source))

    @staticmethod
    def _link_questions(session: Session, document: DocumentRow, group: StudyGroupRow, questions: list[int]) -> None:
        """Link the questions a document was handled in."""
        for number in questions:
            question = session.exec(
                select(QuestionRow).where(
                    QuestionRow.study_group_id == group.id,
                    QuestionRow.number == number,
                )
            ).first()
            if question is None:
                question = QuestionRow(study_group_id=_row_id(group), number=number)
                session.add(question)
                session.flush()
            link = session.exec(
                select(DocumentQuestionRow).where(
                    DocumentQuestionRow.document_id == document.id,
                    DocumentQuestionRow.question_id == question.id,
                )
            ).first()
            if link is None:
                session.add(DocumentQuestionRow(document_id=_row_id(document), question_id=_row_id(question)))

    @staticmethod
    def _link_files(session: Session, document: DocumentRow, metadata: DocumentMetadata) -> None:
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
                    document_id=_row_id(document),
                    format_code=file.format_code,
                    language_code=file.language_code,
                    url=file.url,
                )
                session.add(existing)
            existing.language_code = file.language_code
            existing.size_bytes = file.size_bytes
            existing.posted = file.posted
            existing.url = file.url

    def store_question(self, question: Question, period_label: str) -> None:
        """Insert or update a question under study and its people.

        Args:
            question: The question to store.
            period_label: The study period the question belongs to.
        """
        with self.session() as session:
            group = session.exec(
                select(StudyGroupRow).where(
                    StudyGroupRow.period_label == period_label,
                    StudyGroupRow.number == question.study_group,
                )
            ).first()
            if group is None:
                group = StudyGroupRow(period_label=period_label, number=question.study_group)
                session.add(group)
                session.flush()

            row = session.exec(
                select(QuestionRow).where(
                    QuestionRow.study_group_id == group.id,
                    QuestionRow.number == question.number,
                )
            ).first()
            if row is None:
                row = QuestionRow(study_group_id=_row_id(group), number=question.number)
                session.add(row)
            row.title = question.title
            row.working_group = question.working_group.code
            session.flush()

            for person in question.people:
                session.add(
                    PersonRow(
                        question_id=_row_id(row),
                        name=person.name,
                        role=person.role.value,
                        organization=person.organization,
                        country=person.country,
                        email=person.email,
                        phone=person.phone,
                        fax=person.fax,
                    )
                )
            session.commit()

    def count_documents(self) -> int:
        """Return the number of stored documents."""
        with self.session() as session:
            return len(session.exec(select(DocumentRow)).all())


#: Tables that are created by :meth:`MetadataStore.__init__`.
TABLES: tuple[type[SQLModel], ...] = (
    StudyPeriodRow,
    StudyGroupRow,
    MeetingRow,
    QuestionRow,
    PersonRow,
    DocumentRow,
    DocumentSourceRow,
    DocumentQuestionRow,
    DocumentFileRow,
)

#: Kept for the benefit of tools that introspect the module.
__all__ = [
    "DATABASE_FILE",
    "DocumentFileRow",
    "DocumentQuestionRow",
    "DocumentRow",
    "DocumentSourceRow",
    "MeetingRow",
    "MetadataStore",
    "PersonRow",
    "QuestionRow",
    "StudyGroupRow",
    "StudyPeriodRow",
]
