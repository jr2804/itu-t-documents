"""Download the file of a document.

The file cache is asked first: a document that was downloaded once is not
downloaded again. Otherwise the detail page names the renditions, the TIES
session downloads the one that was asked for, and the file cache keeps it.
"""

from __future__ import annotations

from pathlib import Path

from itu_t_documents.errors import AccessDeniedError
from itu_t_documents.fetching import fetch_document_detail
from itu_t_documents.http.client import ItuClient
from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.enums import DocFormat, DocLanguage
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.files import FileCache


def download_document(
    client: ItuClient,
    store: MetadataStore,
    cache: FileCache,
    ref: DocumentRef,
    *,
    file_format: DocFormat = DocFormat.PDF,
    language: DocLanguage = DocLanguage.ENGLISH,
    output_file: Path | None = None,
) -> Path:
    """Download a document, reusing the cached copy when possible.

    Args:
        client: The HTTP client that authenticates with TIES and downloads.
        store: The metadata store; it keeps the renditions the detail page
            names.
        cache: The file cache that holds the downloaded document.
        ref: The identity of the document.
        file_format: The requested format.
        language: The requested language.
        output_file: A path to write the document to. Defaults to the file cache.

    Returns:
        The path of the downloaded document.

    Raises:
        FileNotFoundError: When the document is not available in the
            requested format and language.
        AccessDeniedError: When the TIES account may not see the
            document. The membership of a TIES account covers only the
            study groups it belongs to.
    """
    cached = cache.find(ref, file_format, language)
    if cached is not None:
        if output_file is None:
            return cached
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(cached.read_bytes())
        return output_file

    metadata = fetch_document_detail(client, ref)
    candidates = [file for file in metadata.files if file.file_format is file_format and file.language is language]
    target = next((file for file in candidates if file.revision is None), None)
    if target is None and candidates:
        target = min(candidates, key=lambda file: file.revision or 0)
    if target is None:
        raise FileNotFoundError(f"{ref.document_id} is not available as {file_format.value}-{language.value}")

    session = client.authenticate(target.url)
    response = session.get(target.url, follow_redirects=True)
    if response.status_code in (401, 403):
        raise AccessDeniedError(
            f"{ref.document_id} is not accessible with these credentials; the membership of the TIES account does not cover {ref.study_group_code}"
        )
    if response.status_code == 404:
        raise FileNotFoundError(f"{ref.document_id} is not available as {file_format.value}-{language.value}")
    response.raise_for_status()
    content = response.content

    stored = cache.store(
        ref,
        file_format,
        language,
        content,
        revision=target.revision,
        extension=target.extension,
    )
    store.store_detail(metadata)
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(content)
        return output_file
    return stored
