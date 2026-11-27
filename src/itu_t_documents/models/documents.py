"""Domain model for ITU-T meeting documents.

The identifiers in this module mirror the ITU-T Document Management System
(DMS) wire format, which was reverse engineered from the public meeting
document pages. A document is addressed by study period, study group, document
type and an increasing number, plus the meeting and sub-type where the DMS
includes them.

============================  ==========================  ==============================
Type                          Identifier                   DMS download path
============================  ==========================  ==============================
Contribution (``C``)          ``T25-SG12-C-0192``          ``/dms_ties/…/sg12/c/…``
Temporary document (``TD``)   ``T25-SG12-261015-TD-GEN-0520``  ``/dms_inf/…/sg12/td/…``
Collective letter (``COL``)   ``T25-SG12-COL-0001``        ``/dms_pub/…/sg12/col/…``
Report (``R``)                ``T25-SG12-R-0001``          ``/dms_ties/…/sg12/r/…``
============================  ==========================  ==============================

Contributions, collective letters and reports are numbered across the whole
study period, so their identifier carries no meeting date. The numbers are not
consecutive: a number that was withdrawn leaves a hole.
Temporary documents are numbered per sub-type across the study period, so
their identifier embeds the meeting date and a sub-type such as ``GEN``.

The study period an identifier names is a ``StudyPeriod`` of
``models/study_periods.py``; what the ITU-T tells about a document is
``DocumentMetadata`` of ``models/metadata.py``. The URLs and the rendition
tables live in :mod:`document_urls` and :mod:`document_formats`.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from itu_t_documents.models.document_formats import _TYPE_PATHS, default_extension
from itu_t_documents.models.document_urls import BASE_URL, LANGUAGE, MEETING_DOC_URL, detail_url
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType, DocVisibility
from itu_t_documents.models.study_periods import StudyPeriod

__all__ = [
    "BASE_URL",
    "LANGUAGE",
    "MEETING_DOC_URL",
    "DocumentRef",
    "MeetingId",
    "default_extension",
    "detail_url",
]

#: ITU-T document identifier, e.g. ``T25-SG12-261015-TD-GEN-0520``.
_DOCUMENT_ID_RE = re.compile(
    r"^T(?P<period>\d{2})-SG(?P<group>\d{1,3})"
    r"(?:-(?P<meeting>\d{6}))?"
    r"-(?P<type>" + "|".join(doc_type.value for doc_type in DocType) + r")"
    r"(?:-(?P<subtype>[A-Z0-9]+))?"
    r"-(?P<number>\d{4})$"
)


class MeetingId(BaseModel):
    """Identifies an ITU-T meeting by its start date."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date | None = None

    @property
    def code(self) -> str:
        """The DMS code for this meeting, e.g. ``261015``."""
        return self.start_date.strftime("%y%m%d")

    @property
    def label(self) -> str:
        """The human readable meeting date, e.g. ``2026-10-15``."""
        return self.start_date.isoformat()

    @classmethod
    def from_code(cls, code: str) -> MeetingId:
        """Parse a DMS meeting code such as ``261015``."""
        text = code.strip()
        if not (len(text) == 6 and text.isdigit()):
            raise ValueError(f"cannot parse meeting code from {code!r}")
        return cls(start_date=date(2000 + int(text[:2]), int(text[2:4]), int(text[4:])))


class DocumentRef(BaseModel):
    """The identity of a single ITU-T document."""

    model_config = ConfigDict(frozen=True)

    study_period: StudyPeriod
    study_group: int = Field(ge=1, le=99)
    doc_type: DocType
    number: int = Field(ge=0)
    subtype: str | None = None
    meeting: MeetingId | None = None

    @property
    def study_group_code(self) -> str:
        """The study group part of a DMS identifier, e.g. ``SG05``.

        The ITU-T writes single digit study groups with a leading zero, so
        study group 5 becomes ``SG05``.
        """
        return f"SG{self.study_group:02d}"

    @property
    def document_id(self) -> str:
        """The DMS identifier of this document."""
        if self.doc_type is DocType.TEMPORARY_DOCUMENT:
            if self.meeting is None:
                raise ValueError("temporary documents require a meeting")
            subtype = self.subtype or "GEN"
            return f"{self.study_period.code}-{self.study_group_code}-{self.meeting.code}-{self.doc_type.value}-{subtype}-{self.number:04d}"
        return f"{self.study_period.code}-{self.study_group_code}-{self.doc_type.value}-{self.number:04d}"

    @property
    def display_number(self) -> str:
        """The number as shown by the ITU-T web interface, e.g. ``520-GEN``."""
        if self.doc_type is DocType.TEMPORARY_DOCUMENT:
            return f"{self.number}-{self.subtype or 'GEN'}"
        return str(self.number)

    @property
    def visibility(self) -> DocVisibility:
        """The access level of this document type in the DMS."""
        return _TYPE_PATHS[self.doc_type][1]

    def download_url(
        self,
        file_format: DocFormat,
        language: DocLanguage,
        revision: int | None = None,
        extension: str | None = None,
    ) -> str:
        """Build the DMS download URL for one rendition of this document.

        Args:
            file_format: The requested file format.
            language: The requested language.
            revision: The revision of the document. The DMS marks a revision
                with ``!R1!`` instead of the plain ``!!`` separator.
            extension: The file name extension. Defaults to the extension the
                DMS uses for the format.

        Returns:
            An absolute URL on ``www.itu.int``.
        """
        segment, visibility = _TYPE_PATHS[self.doc_type]
        suffix = extension or default_extension(file_format)
        path = f"/dms_{visibility.value}/itu-t/md/{self.study_period.short_code}/sg{self.study_group:02d}/{segment}"
        if self.doc_type is DocType.TEMPORARY_DOCUMENT:
            if self.meeting is None:
                raise ValueError("temporary documents require a meeting")
            path = f"{path}/{self.meeting.code}/{self.subtype or 'GEN'}"
        marker = "!!" if revision is None else f"!R{revision}!"
        return f"{BASE_URL}{path}/{self.document_id}{marker}{file_format.value}-{language.value}.{suffix}"

    def detail_url(self) -> str:
        """Build the URL of the DMS detail page for this document."""
        return detail_url(self.document_id)

    @classmethod
    def parse(cls, document_id: str) -> DocumentRef:
        """Parse a DMS document identifier such as ``T25-SG12-261015-TD-GEN-0520``.

        The period code of the identifier names the first year of the study
        period, so the period itself is looked up in the registry of the
        known periods.
        """
        match = _DOCUMENT_ID_RE.match(document_id.strip())
        if match is None:
            raise ValueError(f"cannot parse document identifier from {document_id!r}")
        period = StudyPeriod.parse(f"T{match['period']}")
        meeting = MeetingId.from_code(match["meeting"]) if match["meeting"] else None
        return cls(
            study_period=period,
            study_group=int(match["group"]),
            doc_type=DocType(match["type"]),
            number=int(match["number"]),
            subtype=match["subtype"],
            meeting=meeting,
        )
