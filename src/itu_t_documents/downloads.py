"""Download the file of a document.

The file cache is asked first: a document that was downloaded once is not
downloaded again. Otherwise the detail page names the renditions, the TIES
session downloads the one that was asked for, and the file cache keeps it.
"""

from __future__ import annotations

from pathlib import Path

from itu_t_documents.errors import AccessDeniedError, InvalidDocumentError
from itu_t_documents.fetching import fetch_document_detail
from itu_t_documents.http.client import ItuClient
from itu_t_documents.models.document_formats import matches_format
from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.enums import DocFormat, DocLanguage
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.files import FileCache

#: Number of bytes that are read from a file to tell a document from a page.
SIGNATURE_LENGTH = 8


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
        InvalidDocumentError: When the ITU-T answers with something else
            than the document — the page of its access policy, most likely.
    """
    cached = cache.find(ref, file_format, language)
    if cached is not None and _is_document(file_format, cached):
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
    if not matches_format(file_format, content):
        # The access policy of the DMS answers a protected document with a
        # page of its own when the session is not effective, and that page
        # is served with the status code 200. It is not a document, and it
        # is not stored as one.
        answered = response.headers.get("content-type", "an unknown content type")
        raise InvalidDocumentError(
            f"{ref.document_id} was not downloaded: the ITU-T answered with {answered} instead of the {file_format.value} file; "
            "the session of the TIES account was not effective"
        )

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


def _is_document(file_format: DocFormat, path_file: Path) -> bool:
    """Whether a cached file really is a file of the given format.

    A file that an older release stored from the page of the access policy
    is not a document. It is downloaded again instead of being handed out.

    Args:
        file_format: The format the file was asked for.
        path_file: The path of the cached file.

    Returns:
        Whether the file is a document of that format.
    """
    with path_file.open("rb") as handle:
        return matches_format(file_format, handle.read(SIGNATURE_LENGTH))
