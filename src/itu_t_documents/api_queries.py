"""The stored-document queries of the high level API.

A query reads the metadata store only. It is one responsibility of
:class:`ItuDocuments`, separate from the synchronisation that writes the
store and from the download of a file.

The class implements :class:`~itu_t_documents.interfaces.DocumentHost`, the
contract of the API, so it can be mixed into :class:`ItuDocuments` without
importing it.
"""

from __future__ import annotations

from itu_t_documents.interfaces import DocumentHost
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.storage.queries import DocumentRecord, SourceCount, find_documents, top_sources


class QueryOperations(DocumentHost):
    """The stored-document queries mixed into :class:`ItuDocuments`."""

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
        *,
        last_meetings: int | None = None,
        study_period: StudyPeriod | None = None,
    ) -> list[SourceCount]:
        """Count the documents every source submitted, most prolific first.

        Reads the metadata store only, so a meeting counts after it was
        synchronised. ``last_meetings`` selects the most recent stored
        meetings of the study period; ``meetings`` names them directly. The
        arguments are documented on
        :func:`itu_t_documents.storage.queries.top_sources`.
        """
        if last_meetings is not None:
            meetings = self._recent_meetings(study_group, study_period or StudyPeriod.current(), last_meetings)
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

    def _recent_meetings(self, study_group: int, study_period: StudyPeriod, count: int) -> tuple[str, ...]:
        """Return the codes of the most recent stored meetings of a study group."""
        codes = {
            record.meeting_code for record in self.find_documents(study_group=study_group, study_period=study_period.label) if record.meeting_code is not None
        }
        return tuple(sorted(codes, reverse=True)[:count])
