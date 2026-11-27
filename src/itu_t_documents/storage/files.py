"""On-disk cache for downloaded documents.

Downloaded documents are stored below the per-user cache directory, keyed by
the DMS identifier of the document and the format and language of the
rendition.
"""

from __future__ import annotations

import re
from pathlib import Path

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentRef, default_extension
from itu_t_documents.models.enums import DocFormat, DocLanguage

#: Name of the directory holding the cached documents.
FILES_DIRECTORY = "files"

#: Pattern of the revision marker in the name of a cached rendition.
_REVISION_RE = re.compile(r"-R(?P<revision>\d+)\.")


class FileCache:
    """Stores downloaded documents in the per-user cache directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Open the cache.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
        """
        self.settings = settings or Settings()
        self.root_dir = self.settings.resolved_cache_dir / FILES_DIRECTORY
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def path_for(
        self,
        ref: DocumentRef,
        file_format: DocFormat,
        language: DocLanguage,
        revision: int | None = None,
        extension: str | None = None,
    ) -> Path:
        """Return the cache path of one rendition of a document.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.
            revision: The revision of the rendition. A revision is kept
                beside the original document.
            extension: The file name extension of the rendition. Defaults to
                the extension the DMS uses for the format.

        Returns:
            The path the rendition is cached at.
        """
        suffix = "" if revision is None else f"-R{revision}"
        name = f"{file_format.value}-{language.value}{suffix}.{extension or default_extension(file_format)}"
        return self.root_dir / ref.document_id / name

    def find(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> Path | None:
        """Return the cached rendition of a document, if there is one.

        The original document is preferred over a revision of it.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            The path of the cached rendition, or ``None`` when nothing is
            cached for it.
        """
        document_dir = self.root_dir / ref.document_id
        if not document_dir.is_dir():
            return None
        base = f"{file_format.value}-{language.value}"
        matches = [*document_dir.glob(f"{base}.*"), *document_dir.glob(f"{base}-R*.*")]
        if not matches:
            return None
        return sorted(matches, key=_revision_rank)[0]

    def has(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> bool:
        """Whether a rendition is already cached.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            ``True`` when the cached file exists.
        """
        return self.find(ref, file_format, language) is not None

    def store(
        self,
        ref: DocumentRef,
        file_format: DocFormat,
        language: DocLanguage,
        content: bytes,
        *,
        revision: int | None = None,
        extension: str | None = None,
    ) -> Path:
        """Store a rendition in the cache.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.
            content: The bytes of the document.
            revision: The revision of the rendition.
            extension: The file name extension of the rendition.

        Returns:
            The path the rendition was written to.
        """
        path_file = self.path_for(ref, file_format, language, revision=revision, extension=extension)
        path_file.parent.mkdir(parents=True, exist_ok=True)
        path_file.write_bytes(content)
        return path_file

    def load(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage) -> bytes | None:
        """Read a rendition from the cache.

        Args:
            ref: The identity of the document.
            file_format: The format of the rendition.
            language: The language of the rendition.

        Returns:
            The bytes of the document, or ``None`` when it is not cached.
        """
        path_file = self.find(ref, file_format, language)
        if path_file is None:
            return None
        return path_file.read_bytes()


def _revision_rank(path_file: Path) -> tuple[int, int]:
    """Rank a cached rendition so that the original comes before a revision."""
    match = _REVISION_RE.search(path_file.name)
    if match is None:
        return (0, 0)
    return (1, int(match["revision"]))
