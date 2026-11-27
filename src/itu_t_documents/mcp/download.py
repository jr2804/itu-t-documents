"""The tool that downloads a document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from itu_t_documents.mcp.support import open_api
from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.enums import DocFormat, DocLanguage


def download_document(
    document_id: str,
    file_format: str = "PDF",
    language: str = "E",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Download a document from the ITU-T document management system.

    The document has to be available as the requested format and language.
    Downloading needs TIES credentials; a document that was downloaded before is
    served from the local cache.

    Args:
        document_id: The DMS identifier, e.g. "T25-SG12-261015-TD-GEN-0520".
        file_format: "PDF", "MSW" (Word), "ZIP" or "HTM".
        language: The language code: "E", "F", "S", "A", "C" or "R".
        output_path: A path to write the document to. Defaults to the cache.

    Returns:
        The path of the downloaded document and its size in bytes.
    """
    with open_api() as api:
        ref = DocumentRef.parse(document_id)
        path = api.download(
            ref,
            file_format=DocFormat(file_format.upper()),
            language=DocLanguage(language.upper()),
            output=Path(output_path) if output_path else None,
        )
        return {"path": str(path), "size_bytes": path.stat().st_size}
