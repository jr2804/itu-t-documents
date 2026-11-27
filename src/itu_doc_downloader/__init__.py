"""itu_doc_downloader package.

Access the documents of ITU-T study group meetings. The package offers a
Python API, a command line interface and an MCP server on top of the same
metadata store and document cache.
"""

from __future__ import annotations

from itu_doc_downloader.__about__ import __version__
from itu_doc_downloader.api import DocumentRecord, ItuDocuments, SourceCount
from itu_doc_downloader.catalogue import CatalogueEntry, ItuCatalogue
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.errors import (
    AccessDeniedError,
    AuthenticationError,
    IncompleteListingError,
    ItuError,
    UnknownEntityError,
)
from itu_doc_downloader.models.catalogue import StructureGroup, StudyGroupStructure
from itu_doc_downloader.models.documents import (
    DocumentFile,
    DocumentMetadata,
    DocumentRef,
    MeetingId,
    StudyGroup,
    StudyPeriod,
)
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType, DocVisibility, Role
from itu_doc_downloader.models.questions import Person, Question, WorkingGroup
from itu_doc_downloader.storage.database import MetadataStore
from itu_doc_downloader.storage.files import FileCache

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
