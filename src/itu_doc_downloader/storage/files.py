"""On-disk cache for downloaded documents.

Downloaded documents are stored below the per-user cache directory, keyed by
the DMS identifier of the document and the format and language of the
rendition.
"""

from __future__ import annotations

from pathlib import Path

from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import DocumentRef
from itu_doc_downloader.models.enums import DocFormat, DocLanguage

#: Name of the directory holding the cached documents.
FILES_DIRECTORY = "files"


class FileCache:
    """Stores downloaded documents in the per-user cache directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Open the cache.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
        """
        self.settings = settings or Settings()
        self.root = self.settings.resolved_cache_dir / FILES_DIRECTORY
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> Path:
        """Return the cache path of one rendition of a document.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            The path the rendition is cached at.
        """
        extension = file_format.value.lower()
        if file_format is DocFormat.WORD:
            extension = "docx"
        elif file_format is DocFormat.PDF:
            extension = "pdf"
        elif file_format is DocFormat.ZIP:
            extension = "zip"
        elif file_format is DocFormat.HTML:
            extension = "htm"
        return self.root / ref.document_id / f"{file_format.value}-{language.value}.{extension}"

    def has(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> bool:
        """Whether a rendition is already cached.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            ``True`` when the cached file exists.
        """
        return self.path_for(ref, file_format, language).is_file()

    def store(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage, content: bytes) -> Path:
        """Store a rendition in the cache.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.
            content: The bytes of the document.

        Returns:
            The path the rendition was written to.
        """
        path = self.path_for(ref, file_format, language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def load(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> bytes | None:
        """Read a rendition from the cache.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            The bytes of the document, or ``None`` when it is not cached.
        """
        path = self.path_for(ref, file_format, language)
        if not path.is_file():
            return None
        return path.read_bytes()
