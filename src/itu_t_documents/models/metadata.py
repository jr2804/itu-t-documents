"""What the ITU-T pages tell about a document.

A listing and a detail page are scraped into ``DocumentMetadata``: the
title, the submitting sources, the questions, the posting date and the
downloadable renditions, each a ``DocumentFile``. A document is known by
the ``DocumentRef`` its metadata refers to.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from itu_t_documents.models.documents import DocumentRef, default_extension
from itu_t_documents.models.enums import DocFormat, DocLanguage

#: Pattern of the file name extension at the end of a file name.
_EXTENSION_RE = re.compile(r"\.(?P<extension>[a-z0-9]+)$", re.IGNORECASE)


class DocumentFile(BaseModel):
    """One downloadable rendition of a document."""

    model_config = ConfigDict(frozen=True)

    format_code: str
    language_code: str
    size_bytes: int | None = None
    posted: date | None = None
    url: str
    revision: int | None = None

    @property
    def file_format(self) -> DocFormat | None:
        """The parsed format code, or ``None`` when the DMS uses an unknown code."""
        return DocFormat.parse(self.format_code)

    @property
    def language(self) -> DocLanguage | None:
        """The parsed language code, or ``None`` when the DMS uses an unknown code."""
        return DocLanguage.parse(self.language_code)

    @property
    def extension(self) -> str:
        """The file name extension of the rendition.

        The DMS publishes a document in the format it was submitted in, so the
        extension of the download URL is the authoritative one and the default
        of the format is only used as a fallback.
        """
        match = _EXTENSION_RE.search(urlsplit(self.url).path.rsplit("/", maxsplit=1)[-1])
        if match is not None:
            return match.group("extension").lower()
        file_format = self.file_format
        if file_format is None:
            return ""
        return default_extension(file_format)


class DocumentMetadata(BaseModel):
    """Metadata scraped for a document from the ITU-T DMS listing and detail pages."""

    ref: DocumentRef
    title: str = ""
    sources: list[str] = Field(default_factory=list)
    questions: list[int] = Field(default_factory=list)
    posted: date | None = None
    revision: int | None = None
    files: list[DocumentFile] = Field(default_factory=list)
    detail_url: str = ""
    summary: str | None = None

    @property
    def document_id(self) -> str:
        """The DMS identifier of the described document."""
        return self.ref.document_id
