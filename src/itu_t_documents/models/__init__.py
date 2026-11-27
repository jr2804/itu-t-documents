"""Domain model of the ITU-T documents."""

from __future__ import annotations

from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import (
    DocFormat,
    DocLanguage,
    DocType,
    DocVisibility,
    Role,
)
from itu_t_documents.models.metadata import DocumentFile, DocumentMetadata
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod

__all__ = [
    "DocFormat",
    "DocLanguage",
    "DocType",
    "DocVisibility",
    "DocumentFile",
    "DocumentMetadata",
    "DocumentRef",
    "MeetingId",
    "Person",
    "Question",
    "Role",
    "StudyPeriod",
    "WorkingGroup",
]
