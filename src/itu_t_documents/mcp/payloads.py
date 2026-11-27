"""The JSON payloads the MCP tools return."""

from __future__ import annotations

from typing import TypedDict

from itu_t_documents.models.questions import Person
from itu_t_documents.storage.queries import DocumentRecord, SourceCount


class PersonPayload(TypedDict):
    """A person and the role they hold for a question."""

    name: str
    role: str
    organization: str | None


class DocumentPayload(TypedDict):
    """A document as returned by the document tools."""

    document_id: str
    type: str
    number: int
    subtype: str | None
    title: str
    sources: list[str]
    questions: list[int]
    posted: str | None
    revision: int | None
    study_group: int
    study_period: str
    meeting: str | None
    detail_url: str


class SourcePayload(TypedDict):
    """The number of documents a source submitted."""

    source: str
    documents: int
    contributions: int
    temporary_documents: int
    meetings: list[str]


class MeetingPayload(TypedDict):
    """A meeting of a study group."""

    meeting: str
    place: str
    start_date: str
    end_date: str | None
    label: str


class QuestionPayload(TypedDict):
    """A question under study with the people who hold its roles."""

    question: str
    number: int
    title: str
    working_group: str
    rapporteurs: list[PersonPayload]
    co_rapporteurs: list[PersonPayload]
    other_people: list[PersonPayload]


class PeriodPayload(TypedDict):
    """A study period of the ITU-T."""

    label: str
    code: str
    start_year: int
    end_year: int
    current: bool


class StudyGroupPayload(TypedDict):
    """A study group of a study period."""

    code: str
    number: int
    title: str
    study_period: str


class WorkingGroupPayload(TypedDict):
    """A working group of a study group."""

    code: str
    name: str | None


class StructureQuestionPayload(TypedDict):
    """A question as it appears in the structure of a study group."""

    code: str
    number: int
    title: str
    working_group: str


class OtherGroupPayload(TypedDict):
    """A regional, focus or coordination group of a study group."""

    code: str
    title: str
    kind: str


class StructurePayload(TypedDict):
    """The structure of a study group."""

    study_group: str
    study_period: str
    plenary: str | None
    working_groups: list[WorkingGroupPayload]
    questions: list[StructureQuestionPayload]
    other_groups: list[OtherGroupPayload]


class CatalogueEntryPayload(TypedDict):
    """An entry of the catalogue search."""

    kind: str
    code: str
    title: str
    study_group: int
    study_period: str


class DownloadPayload(TypedDict):
    """The path and size of a downloaded document."""

    path: str
    size_bytes: int


def document_payload(record: DocumentRecord) -> DocumentPayload:
    """Convert a document record into a JSON friendly payload."""
    return {
        "document_id": record.document_id,
        "type": record.doc_type.value,
        "number": record.number,
        "subtype": record.subtype,
        "title": record.title,
        "sources": list(record.sources),
        "questions": list(record.questions),
        "posted": record.posted.isoformat() if record.posted else None,
        "revision": record.revision,
        "study_group": record.study_group,
        "study_period": record.study_period,
        "meeting": record.meeting_code,
        "detail_url": record.detail_url,
    }


def source_payload(count: SourceCount) -> SourcePayload:
    """Convert a source count into a JSON friendly payload."""
    return {
        "source": count.source,
        "documents": count.count,
        "contributions": count.contributions,
        "temporary_documents": count.temporary_documents,
        "meetings": list(count.meetings),
    }


def person_payload(person: Person) -> PersonPayload:
    """Convert a person into a JSON friendly payload."""
    return {"name": person.name, "role": person.role.value, "organization": person.organization}
