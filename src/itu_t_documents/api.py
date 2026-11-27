"""High level API for ITU-T meeting documents.

The API is the entry point used by the CLI and the MCP server. It combines
three sources of truth:

* the ITU-T web site, scraped through the HTTP cache,
* the SQLite metadata store, which keeps everything that was seen before,
* the file cache, which holds already downloaded documents.

:class:`ItuDocuments` is the door to them. The work is done by modules with
one responsibility each, and their functions document the arguments:
:mod:`itu_t_documents.fetching` reads the ITU-T web site,
:mod:`itu_t_documents.downloads` fetches the file of a document and
:mod:`itu_t_documents.storage.queries` asks the metadata store. A method of
:class:`ItuDocuments` passes its arguments on to them unchanged.
"""

from __future__ import annotations

from pathlib import Path

from itu_t_documents.catalogue import ItuCatalogue
from itu_t_documents.config.settings import Settings
from itu_t_documents.downloads import download_document
from itu_t_documents.fetching import fetch_document_detail, fetch_documents, list_meetings, list_questions
from itu_t_documents.http.client import ItuClient, ItuHttpClient
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.questions import Question
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping import meetings as meetings_scraper
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.files import FileCache
from itu_t_documents.storage.queries import DocumentRecord, SourceCount, find_documents, top_sources


class ItuDocuments:
    """High level access to the documents of ITU-T study group meetings."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: ItuClient | None = None,
        store: MetadataStore | None = None,
        cache: FileCache | None = None,
    ) -> None:
        """Create the API.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
            client: The HTTP client to use. Defaults to a new one.
            store: The metadata store to use. Defaults to a new one.
            cache: The file cache to use. Defaults to a new one.
        """
        self.settings = settings or Settings()
        self.client = client or ItuHttpClient(self.settings)
        self.store = store or MetadataStore(self.settings)
        self.cache = cache or FileCache(self.settings)
        self.catalogue = ItuCatalogue(self.settings, client=self.client)
        self._owns_client = client is None
        self._owns_store = store is None

    def close(self) -> None:
        """Release the resources owned by this API."""
        if self._owns_client:
            self.client.close()
        if self._owns_store:
            self.store.close()

    def __enter__(self) -> ItuDocuments:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def list_meetings(self, study_group: int, study_period: StudyPeriod) -> list[meetings_scraper.MeetingInfo]:
        """List the meetings of a study group, in the order of the ITU-T pages.

        Reads the ITU-T web site. The arguments are documented on
        :func:`itu_t_documents.fetching.list_meetings`.
        """
        return list_meetings(self.client, study_group, study_period)

    def list_questions(self, study_group: int, study_period: StudyPeriod) -> list[Question]:
        """List the questions under study of a study group, ordered by number.

        Reads the ITU-T web site. The arguments are documented on
        :func:`itu_t_documents.fetching.list_questions`.
        """
        return list_questions(self.client, study_group, study_period)

    def fetch_documents(self, study_group: int, doc_type: DocType, study_period: StudyPeriod, meeting: MeetingId | None = None) -> list[DocumentMetadata]:
        """Fetch a document listing, every page of it, without storing it.

        Reads the ITU-T web site and raises :class:`IncompleteListingError`
        when a listing reports more documents than its pages hold. The
        arguments are documented on
        :func:`itu_t_documents.fetching.fetch_documents`.
        """
        return fetch_documents(self.client, study_group, doc_type, study_period, meeting)

    def fetch_document_detail(self, ref: DocumentRef) -> DocumentMetadata:
        """Fetch the detail page of a document, which names its renditions.

        Reads the ITU-T web site. The arguments are documented on
        :func:`itu_t_documents.fetching.fetch_document_detail`.
        """
        return fetch_document_detail(self.client, ref)

    def sync_meeting(
        self,
        study_group: int,
        meeting: MeetingId,
        study_period: StudyPeriod,
        doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
    ) -> int:
        """Fetch and store the documents of a meeting.

        Args:
            study_group: The study group number.
            meeting: The meeting.
            study_period: The study period.
            doc_types: The document types to fetch.

        Returns:
            The number of documents stored.
        """
        stored = 0
        for doc_type in doc_types:
            for metadata in self.fetch_documents(study_group, doc_type, study_period, meeting):
                self.store.store_document(metadata)
                stored += 1
        return stored

    def sync_questions(self, study_group: int, study_period: StudyPeriod) -> int:
        """Fetch and store the questions under study of a study group.

        Args:
            study_group: The study group number.
            study_period: The study period.

        Returns:
            The number of questions stored.
        """
        questions = self.list_questions(study_group, study_period)
        for question in questions:
            self.store.store_question(question, study_period.label)
        return len(questions)

    def sync_detail(self, ref: DocumentRef) -> DocumentMetadata:
        """Fetch the renditions of a document and store them.

        Args:
            ref: The identity of the document.

        Returns:
            The metadata of the document.
        """
        metadata = self.fetch_document_detail(ref)
        self.store.store_detail(metadata)
        return metadata

    def find_documents(
        self,
        *,
        study_group: int | None = None,
        study_period: str | None = None,
        doc_type: DocType | None = None,
        doc_types: tuple[DocType, ...] | None = None,
        meeting: str | None = None,
        question: int | None = None,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[DocumentRecord]:
        """Search the stored documents, newest number first.

        Reads the metadata store only; the network is not contacted. The
        filters are documented on
        :func:`itu_t_documents.storage.queries.find_documents`.
        """
        return find_documents(
            self.store,
            study_group=study_group,
            study_period=study_period,
            doc_type=doc_type,
            doc_types=doc_types,
            meeting=meeting,
            question=question,
            source=source,
            limit=limit,
        )

    def top_sources(
        self,
        study_group: int,
        meetings: tuple[str, ...] | None = None,
        doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
        limit: int = 10,
    ) -> list[SourceCount]:
        """Count the documents every source submitted, most prolific first.

        Reads the metadata store only, so a meeting counts after it was
        synchronised. The arguments are documented on
        :func:`itu_t_documents.storage.queries.top_sources`.
        """
        return top_sources(self.store, study_group, meetings, doc_types, limit)

    def documents_for_question(
        self,
        study_group: int,
        question: int,
        meeting: str | None = None,
        doc_type: DocType | None = None,
        study_period: str | None = None,
    ) -> list[DocumentRecord]:
        """List the documents handled in a question.

        Reads the metadata store only. ``meeting`` (a DMS code), ``doc_type``
        and ``study_period`` restrict the search; without a study period every
        stored study period is searched.
        """
        return self.find_documents(
            study_group=study_group,
            question=question,
            meeting=meeting,
            doc_type=doc_type,
            study_period=study_period,
        )

    def contributions_by_source(self, study_group: int, source: str, study_period: str | None = None) -> list[DocumentRecord]:
        """List the contributions submitted by an organisation.

        Reads the metadata store only. ``source`` is matched case
        insensitively and partially; without ``study_period`` every stored
        study period is searched.
        """
        return self.find_documents(study_group=study_group, doc_type=DocType.CONTRIBUTION, source=source, study_period=study_period)

    def download(
        self,
        ref: DocumentRef,
        file_format: DocFormat = DocFormat.PDF,
        language: DocLanguage = DocLanguage.ENGLISH,
        output: Path | None = None,
    ) -> Path:
        """Download a document, reusing the cached copy when possible.

        Raises :class:`FileNotFoundError` when the document is not available
        in the requested format and language, and :class:`AccessDeniedError`
        when the TIES account may not see the document. The arguments are
        documented on :func:`itu_t_documents.downloads.download_document`.
        """
        return download_document(self.client, self.store, self.cache, ref, file_format=file_format, language=language, output=output)
