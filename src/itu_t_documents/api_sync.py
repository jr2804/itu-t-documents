"""The synchronisation methods of the high level API.

A synchronisation reads the ITU-T web site and writes the result to the
metadata store. It is one responsibility of :class:`ItuDocuments`, separate
from the lookups that read the store and from the download of a file.

The class implements :class:`~itu_t_documents.interfaces.DocumentHost`, the
contract of the API, so it can be mixed into :class:`ItuDocuments` without
importing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from itu_t_documents.interfaces import DocumentHost
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.study_periods import StudyPeriod


@dataclass(frozen=True)
class SyncReport:
    """What a study-group synchronisation stored."""

    meetings: tuple[tuple[str, int], ...] = ()
    period_only: int = 0

    @property
    def total(self) -> int:
        """The number of documents stored by the whole synchronisation."""
        return sum(stored for _, stored in self.meetings) + self.period_only


class SyncOperations(DocumentHost):
    """The synchronisation methods mixed into :class:`ItuDocuments`."""

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
        before = self.store.count_documents()
        for doc_type in doc_types:
            for metadata in self.fetch_documents(study_group, doc_type, study_period, meeting):
                self.store.store_document(metadata)
        return self.store.count_documents() - before

    def sync_period(
        self,
        study_group: int,
        study_period: StudyPeriod,
        doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
    ) -> int:
        """Fetch and store the period-wide listing of a study group.

        A contribution can be posted between two meetings: the listing of the
        period names it, while no meeting listing does. The period-wide
        listing is therefore read as well, and a document it names without a
        meeting is stored with no meeting.

        Args:
            study_group: The study group number.
            study_period: The study period.
            doc_types: The document types to fetch. Temporary documents are
                previewed by the aggregate listing and are read meeting by
                meeting instead.

        Returns:
            The number of documents stored.
        """
        before = self.store.count_documents()
        for doc_type in doc_types:
            if doc_type is DocType.TEMPORARY_DOCUMENT:
                continue
            for metadata in self.fetch_documents(study_group, doc_type, study_period):
                self.store.store_document(metadata)
        return self.store.count_documents() - before

    def sync_study_group(
        self,
        study_group: int,
        study_period: StudyPeriod,
        doc_types: tuple[DocType, ...] = (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT),
    ) -> SyncReport:
        """Fetch and store a study group: every meeting and the period listing.

        Args:
            study_group: The study group number.
            study_period: The study period.
            doc_types: The document types to fetch.

        Returns:
            A report of the documents stored per meeting and by the
            period-wide listing alone.
        """
        meetings: list[tuple[str, int]] = []
        meeting_types = tuple(doc_type for doc_type in doc_types if doc_type in (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT))
        if meeting_types:
            for meeting in self.list_meetings(study_group, study_period):
                meetings.append((meeting.code, self.sync_meeting(study_group, MeetingId.from_code(meeting.code), study_period, meeting_types)))
        period_only = self.sync_period(study_group, study_period, doc_types)
        return SyncReport(meetings=tuple(meetings), period_only=period_only)

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
