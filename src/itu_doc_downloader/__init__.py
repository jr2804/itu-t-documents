"""itu_doc_downloader package.

Access the documents of ITU-T study group meetings. The package offers a
Python API, a command line interface and an MCP server on top of the same
metadata store and document cache.
"""

from __future__ import annotations

from itu_doc_downloader.__about__ import __version__
from itu_doc_downloader.api import DocumentRecord, IncompleteListingError, ItuDocuments, SourceCount
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import (
    DocumentFile,
    DocumentMetadata,
    DocumentRef,
    MeetingId,
    StudyPeriod,
)
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType, DocVisibility, Role
from itu_doc_downloader.models.questions import Person, Question, WorkingGroup
from itu_doc_downloader.storage.database import MetadataStore
from itu_doc_downloader.storage.files import FileCache

__all__ = [
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
    "ItuDocuments",
    "MeetingId",
    "MetadataStore",
    "Person",
    "Question",
    "Role",
    "Settings",
    "SourceCount",
    "StudyPeriod",
    "WorkingGroup",
    "__version__",
]
