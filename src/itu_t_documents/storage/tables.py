"""The rows of the metadata database.

Every table of the metadata store is a SQLModel class in this module.
``MetadataStore`` creates the tables when it opens the database; the
writers in ``documents.py`` and ``questions.py`` fill them and the
queries in ``queries.py`` read them.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from sqlmodel import Field, SQLModel


class HasIdentifier(Protocol):
    """A row with a primary key."""

    @property
    def id(self) -> int | None: ...


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
    revision: int | None = None


def row_id(row: HasIdentifier) -> int:
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
