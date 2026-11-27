"""itu_t_documents package.

Access the documents of ITU-T study group meetings. The package offers a
Python API, a command line interface and an MCP server on top of the same
metadata store and document cache.
"""

from __future__ import annotations

from itu_t_documents.__about__ import __version__
from itu_t_documents.api import ItuDocuments
from itu_t_documents.catalogue import CatalogueEntry, ItuCatalogue
from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import (
    AccessDeniedError,
    AuthenticationError,
    IncompleteListingError,
    ItuError,
    ScrapingError,
    UnknownEntityError,
)
from itu_t_documents.models.catalogue import StructureGroup, StudyGroup, StudyGroupStructure
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType, DocVisibility, Role
from itu_t_documents.models.metadata import DocumentFile, DocumentMetadata
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.files import FileCache
from itu_t_documents.storage.queries import DocumentRecord, SourceCount

__all__ = [
    "AccessDeniedError",
    "AuthenticationError",
    "CatalogueEntry",
    "DocFormat",
    "DocLanguage",
    "DocType",
    "DocVisibility",
    "DocumentFile",
    "DocumentMetadata",
    "DocumentRecord",
    "DocumentRef",
    "FileCache",
    "IncompleteListingError",
    "ItuCatalogue",
    "ItuDocuments",
    "ItuError",
    "MeetingId",
    "MetadataStore",
    "Person",
    "Question",
    "Role",
    "ScrapingError",
    "Settings",
    "SourceCount",
    "StructureGroup",
    "StudyGroup",
    "StudyGroupStructure",
    "StudyPeriod",
    "UnknownEntityError",
    "WorkingGroup",
    "__version__",
]
