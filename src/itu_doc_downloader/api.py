"""High level API for ITU-T meeting documents.

The API is the entry point used by the CLI and the MCP server. It combines
three sources of truth:

* the ITU-T web site, scraped through the HTTP cache,
* the SQLite metadata store, which keeps everything that was seen before,
* the file cache, which holds already downloaded documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.http.client import ItuClient, ItuHttpClient
from itu_doc_downloader.models.documents import DocumentMetadata, DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType
from itu_doc_downloader.models.questions import Question
from itu_doc_downloader.scraping import detail as detail_scraper
from itu_doc_downloader.scraping import listing as listing_scraper
from itu_doc_downloader.scraping import meetings as meetings_scraper
from itu_doc_downloader.scraping import questions as questions_scraper
from itu_doc_downloader.storage.database import (
    DocumentQuestionRow,
    DocumentRow,
    DocumentSourceRow,
    MeetingRow,
    MetadataStore,
    QuestionRow,
    StudyGroupRow,
)
from itu_doc_downloader.storage.files import FileCache
from itu_doc_downloader.urls import detail_url, listing_url, period_index, questions_url

#: Template of the path of the meeting index page of a study group.
MEETING_INDEX_PATH = "/md/{prefix}-{group}/en"


@dataclass(frozen=True)
class DocumentRecord:
    """A document as stored in the metadata database."""

    document_id: str
    doc_type: DocType
    number: int
    subtype: str | None
    title: str
    sources: tuple[str, ...] = ()
    questions: tuple[int, ...] = ()
    posted: date | None = None
    revision: int | None = None
    study_group: int = 0
    study_period: str = ""
    meeting_code: str | None = None
    detail_url: str = ""


@dataclass(frozen=True)
class SourceCount:
    """The number of documents a single source submitted."""

    source: str
    count: int
    contributions: int = 0
    temporary_documents: int = 0
    meetings: tuple[str, ...] = ()


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
        self._owns_client = client is None

    def close(self) -> None:
        """Release the resources owned by this API."""
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> ItuDocuments:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_meetings(self, study_group: int, study_period: StudyPeriod) -> list[meetings_scraper.MeetingInfo]:
        """List the meetings of a study group.

        Args:
            study_group: The study group number.
            study_period: The study period.

        Returns:
            The meetings found, in the order of the ITU-T pages.
        """
        url = f"https://www.itu.int{MEETING_INDEX_PATH.format(prefix=study_period.code, group=f'SG{study_group:02d}')}"
        page = self.client.get_text(url)
        return meetings_scraper.parse_meeting_index(page)

    def list_questions(self, study_group: int, study_period: StudyPeriod) -> list[Question]:
        """List the questions under study of a study group.

        Args:
            study_group: The study group number.
            study_period: The study period.

        Returns:
            The questions found, ordered by question number.
        """
        index = period_index(study_period)
        page = self.client.get_text(questions_url(study_group, index))
        return questions_scraper.parse_questions(page, study_group)

    def fetch_documents(
        self,
        study_group: int,
        doc_type: DocType,
        study_period: StudyPeriod,
        meeting: MeetingId | None = None,
    ) -> list[DocumentMetadata]:
        """Fetch a document listing from the ITU-T web site.

        Args:
            study_group: The study group number.
            doc_type: The document type to list.
            study_period: The study period.
            meeting: The meeting to list the documents of.

        Returns:
            The metadata of the listed documents.
        """
        page = self.client.get_text(listing_url(study_period, study_group, doc_type, meeting))
        return listing_scraper.parse_listing(page, study_period, study_group, doc_type, meeting)

    def fetch_document_detail(self, ref: DocumentRef) -> DocumentMetadata:
        """Fetch the detail page of a document.

        Args:
            ref: The identity of the document.

        Returns:
            The metadata of the document, including its available renditions.
        """
        page = self.client.get_text(detail_url(ref.document_id))
        return DocumentMetadata(
            ref=ref,
            title=detail_scraper.parse_title(page),
            files=detail_scraper.parse_files(page),
            detail_url=detail_url(ref.document_id),
        )

    # ------------------------------------------------------------------
    # Synchronisation
    # ------------------------------------------------------------------

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
        self.store.store_document(metadata)
        return metadata

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

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
        """Search the stored documents.

        Args:
            study_group: Restrict to a study group.
            study_period: Restrict to a study period, e.g. ``2025-2028``.
            doc_type: Restrict to a single document type.
            doc_types: Restrict to several document types.
            meeting: Restrict to a meeting, given by its DMS code, e.g. ``270119``.
            question: Restrict to the documents handled in a question.
            source: Restrict to the documents submitted by a source; the match
                is case insensitive and partial.
            limit: Maximum number of results.

        Returns:
            The matching documents, newest number first.
        """
        with self.store.session() as session:
            statement = select(DocumentRow)
            if study_group is not None or study_period is not None:
                statement = statement.join(StudyGroupRow)
            if study_group is not None:
                statement = statement.where(StudyGroupRow.number == study_group)
            if study_period is not None:
                statement = statement.where(StudyGroupRow.period_label == study_period)
            if doc_type is not None:
                statement = statement.where(DocumentRow.doc_type == doc_type.value)
            if doc_types is not None:
                # SQLModel declares its table columns with plain Python types, so the
                # SQLAlchemy helpers on the columns are invisible to the type checker.
                values = [doc_type.value for doc_type in doc_types]
                statement = statement.where(DocumentRow.doc_type.in_(values))  # ty: ignore[missing-attribute]
            if meeting is not None:
                statement = statement.join(MeetingRow).where(MeetingRow.code == meeting)
            if question is not None:
                statement = statement.join(DocumentQuestionRow).join(QuestionRow).where(QuestionRow.number == question)
            if source is not None:
                pattern = f"%{source}%"
                statement = statement.join(DocumentSourceRow).where(DocumentSourceRow.source.ilike(pattern))  # ty: ignore[missing-attribute]
            statement = statement.order_by(DocumentRow.number.desc())  # ty: ignore[missing-attribute]
            if limit is not None:
                statement = statement.limit(limit)

            rows = session.exec(statement).all()
            return [self._to_record(session, row) for row in rows]

    def top_sources(
        self,
        study_group: int,
        meetings: tuple[str, ...] | None = None,
        doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
        limit: int = 10,
    ) -> list[SourceCount]:
        """Count the documents every source submitted.

        Args:
            study_group: The study group number.
            meetings: The DMS codes of the meetings to consider. Defaults to
                every stored meeting of the study group.
            doc_types: The document types to count.
            limit: The maximum number of sources to report.

        Returns:
            The sources with their document counts, most prolific first.
        """
        with self.store.session() as session:
            statement = (
                select(DocumentRow)
                .join(DocumentSourceRow)
                .join(StudyGroupRow)
                .where(StudyGroupRow.number == study_group)
                .where(DocumentRow.doc_type.in_([doc_type.value for doc_type in doc_types]))  # ty: ignore[missing-attribute]
            )
            rows = session.exec(statement).all()
            records = [self._to_record(session, row) for row in rows]

        counts: dict[str, SourceCount] = {}
        for record in records:
            if meetings is not None and record.meeting_code not in meetings:
                continue
            for source in record.sources:
                current = counts.get(source)
                if current is None:
                    current = SourceCount(source=source, count=0)
                    counts[source] = current
                updated = SourceCount(
                    source=current.source,
                    count=current.count + 1,
                    contributions=current.contributions + (1 if record.doc_type is DocType.CONTRIBUTION else 0),
                    temporary_documents=current.temporary_documents + (1 if record.doc_type is DocType.TEMPORARY_DOCUMENT else 0),
                    meetings=current.meetings + ((record.meeting_code,) if record.meeting_code and record.meeting_code not in current.meetings else ()),
                )
                counts[source] = updated

        ordered = sorted(counts.values(), key=lambda item: (-item.count, item.source))
        return ordered[:limit]

    def documents_for_question(
        self,
        study_group: int,
        question: int,
        meeting: str | None = None,
        doc_type: DocType | None = None,
    ) -> list[DocumentRecord]:
        """List the documents handled in a question.

        Args:
            study_group: The study group number.
            question: The question number.
            meeting: Restrict to a meeting, given by its DMS code.
            doc_type: Restrict to a document type.

        Returns:
            The matching documents.
        """
        return self.find_documents(
            study_group=study_group,
            question=question,
            meeting=meeting,
            doc_type=doc_type,
        )

    def contributions_by_source(self, study_group: int, source: str) -> list[DocumentRecord]:
        """List the contributions submitted by an organisation.

        Args:
            study_group: The study group number.
            source: The name of the submitting organisation; the match is case
                insensitive and partial.

        Returns:
            The matching documents.
        """
        return self.find_documents(study_group=study_group, doc_type=DocType.CONTRIBUTION, source=source)

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def download(
        self,
        ref: DocumentRef,
        file_format: DocFormat = DocFormat.PDF,
        language: DocLanguage = DocLanguage.ENGLISH,
        output: Path | None = None,
    ) -> Path:
        """Download a document, reusing the cached copy when possible.

        Args:
            ref: The identity of the document.
            file_format: The requested format.
            language: The requested language.
            output: A path to write the document to. Defaults to the file cache.

        Returns:
            The path of the downloaded document.

        Raises:
            FileNotFoundError: When the document is not available in the
                requested format and language.
        """
        cached = self.cache.path_for(ref, file_format, language)
        if self.cache.has(ref, file_format, language):
            if output is None:
                return cached
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(cached.read_bytes())
            return output

        metadata = self.fetch_document_detail(ref)
        target = next(
            (file for file in metadata.files if file.file_format is file_format and file.language is language),
            None,
        )
        if target is None:
            raise FileNotFoundError(f"{ref.document_id} is not available as {file_format.value}-{language.value}")

        session = self.client.authenticate(target.url)
        response = session.get(target.url, follow_redirects=True)
        response.raise_for_status()
        content = response.content

        stored = self.cache.store(ref, file_format, language, content)
        self.store.store_document(metadata)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
            return output
        return stored

    @staticmethod
    def _to_record(session: Session, row: DocumentRow) -> DocumentRecord:
        """Build a :class:`DocumentRecord` from a database row."""
        sources = tuple(source.source for source in session.exec(select(DocumentSourceRow).where(DocumentSourceRow.document_id == row.id)).all())
        questions = tuple(
            question.number for question in session.exec(select(QuestionRow).join(DocumentQuestionRow).where(DocumentQuestionRow.document_id == row.id)).all()
        )
        group = session.get(StudyGroupRow, row.study_group_id)
        meeting_code = None
        if row.meeting_id is not None:
            meeting = session.get(MeetingRow, row.meeting_id)
            meeting_code = meeting.code if meeting is not None else None
        return DocumentRecord(
            document_id=row.document_id,
            doc_type=DocType(row.doc_type),
            number=row.number,
            subtype=row.subtype,
            title=row.title,
            sources=sources,
            questions=questions,
            posted=row.posted,
            revision=row.revision,
            study_group=group.number if group is not None else 0,
            study_period=group.period_label if group is not None else "",
            meeting_code=meeting_code,
            detail_url=row.detail_url,
        )
