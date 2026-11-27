"""Renditions of an ITU-T document: extensions, paths and visibility."""

from __future__ import annotations

from itu_t_documents.models.enums import DocFormat, DocType, DocVisibility

#: Extension the DMS uses for each download format by default. A document is
#: published in the format it was submitted in, so a Word document may also be
#: a ``.doc`` or a ``.msw`` file; the extension of the download URL is the
#: authoritative one.
_FORMAT_EXTENSIONS: dict[DocFormat, str] = {
    DocFormat.WORD: "docx",
    DocFormat.PDF: "pdf",
    DocFormat.ZIP: "zip",
    DocFormat.HTML: "htm",
}

#: DMS path segment and visibility for each document type.
_TYPE_PATHS: dict[DocType, tuple[str, DocVisibility]] = {
    DocType.CONTRIBUTION: ("c", DocVisibility.TIES),
    DocType.TEMPORARY_DOCUMENT: ("td", DocVisibility.INTERNAL),
    DocType.COLLECTIVE_LETTER: ("col", DocVisibility.PUBLIC),
    DocType.REPORT: ("r", DocVisibility.TIES),
}


def default_extension(file_format: DocFormat) -> str:
    """Return the file name extension the DMS uses for a format by default.

    Args:
        file_format: The download format.

    Returns:
        The extension, without a leading dot.
    """
    return _FORMAT_EXTENSIONS[file_format]
