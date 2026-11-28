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

#: The bytes a file of each format begins with. The access policy of the DMS
#: answers a protected document with a page when the session is not effective,
#: and that page is served with the status code 200 — only the bytes of the
#: answer tell a document from the page. A Word document is a ZIP archive or,
#: when it was submitted in the old format, an OLE compound file.
_FORMAT_SIGNATURES: dict[DocFormat, tuple[bytes, ...]] = {
    DocFormat.WORD: (b"PK", b"\xd0\xcf\x11\xe0"),
    DocFormat.PDF: (b"%PDF",),
    DocFormat.ZIP: (b"PK",),
    DocFormat.HTML: (b"<",),
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


def matches_format(file_format: DocFormat, content: bytes) -> bool:
    """Whether the bytes are the beginning of a file of the given format.

    Args:
        file_format: The format the file was asked for.
        content: The first bytes of the answer of the ITU-T.

    Returns:
        Whether the bytes belong to a file of that format.
    """
    stripped = content.lstrip()
    return any(stripped.startswith(signature) for signature in _FORMAT_SIGNATURES[file_format])
