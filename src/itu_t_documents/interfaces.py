"""The contracts the parts of the package agree on.

A part that is mixed into a class refers to that class through a protocol:
importing the class would be circular, and the protocol keeps the dependency
one way. The class that is mixed into implements the protocol, and the type
checker verifies that it does.

A ``TYPE_CHECKING`` guard is not the answer to a circular import: it hides
the cycle instead of breaking it, and the code then behaves differently at
runtime than it does for the type checker.
"""

from __future__ import annotations

from typing import Protocol

from itu_t_documents.http.client import ItuClient
from itu_t_documents.models.catalogue import StudyGroup, StudyGroupStructure
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.questions import Question
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping.meetings import MeetingInfo
from itu_t_documents.storage.database import MetadataStore


class DocumentHost(Protocol):
    """What the API needs from the class its operations are mixed into."""

    store: MetadataStore
    """The metadata store the operations read and write."""

    client: ItuClient
    """The HTTP client the operations read the ITU-T with."""

    def list_meetings(self, study_group: int, study_period: StudyPeriod) -> list[MeetingInfo]:
        """The meetings of a study group."""
        ...

    def list_questions(self, study_group: int, study_period: StudyPeriod) -> list[Question]:
        """The questions under study of a study group."""
        ...

    def fetch_documents(
        self,
        study_group: int,
        doc_type: DocType,
        study_period: StudyPeriod,
        meeting: MeetingId | None = None,
    ) -> list[DocumentMetadata]:
        """The documents of a meeting or of a study period."""
        ...

    def fetch_document_detail(self, ref: DocumentRef) -> DocumentMetadata:
        """The detail page of a document."""
        ...


class CatalogueHost(Protocol):
    """What the catalogue search needs from the class it is mixed into."""

    def study_groups(self, period: StudyPeriod) -> list[StudyGroup]:
        """The study groups of a study period."""
        ...

    def structure(self, study_group: int, period: StudyPeriod) -> StudyGroupStructure:
        """The structure of a study group."""
        ...

    @staticmethod
    def current_period() -> StudyPeriod:
        """The study period of the current year."""
        ...
