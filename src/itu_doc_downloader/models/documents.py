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
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType, DocVisibility

#: ITU-T document identifier, e.g. ``T25-SG12-261015-TD-GEN-0520``.
_DOCUMENT_ID_RE = re.compile(
    r"^T(?P<period>\d{2})-SG(?P<group>\d{1,3})"
    r"(?:-(?P<meeting>\d{6}))?"
    r"-(?P<type>TD|COL|R|C)"
    r"(?:-(?P<subtype>[A-Z0-9]+))?"
    r"-(?P<number>\d{4})$"
)

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

#: Pattern of the file name extension at the end of a file name.
_EXTENSION_RE = re.compile(r"\.(?P<extension>[a-z0-9]+)$", re.IGNORECASE)


def default_extension(file_format: DocFormat) -> str:
    """Return the file name extension the DMS uses for a format by default.

    Args:
        file_format: The download format.

    Returns:
        The extension, without a leading dot.
    """
    return _FORMAT_EXTENSIONS[file_format]


#: DMS path segment and visibility for each document type.
_TYPE_PATHS: dict[DocType, tuple[str, DocVisibility]] = {
    DocType.CONTRIBUTION: ("c", DocVisibility.TIES),
    DocType.TEMPORARY_DOCUMENT: ("td", DocVisibility.INTERNAL),
    DocType.COLLECTIVE_LETTER: ("col", DocVisibility.PUBLIC),
    DocType.REPORT: ("r", DocVisibility.TIES),
}


class StudyPeriod(BaseModel):
    """An ITU-T study period, e.g. ``2025-2028``."""

    model_config = ConfigDict(frozen=True)

    start_year: int = Field(ge=1900, le=2999)
    end_year: int = Field(ge=1900, le=2999)

    @field_validator("end_year")
    @classmethod
    def _check_end_year(cls, value: int, info: object) -> int:
        """Ensure the period spans a sensible number of years."""
        data = getattr(info, "data", {}) or {}
        start = data.get("start_year")
        if isinstance(start, int) and value < start:
            raise ValueError("end_year must not precede start_year")
        return value

    @classmethod
    def parse(cls, value: str) -> StudyPeriod:
        """Parse ``"2025-2028"`` or the DMS code ``"T25"``."""
        text = value.strip()
        if text.upper().startswith("T") and text[1:].isdigit():
            start = 2000 + int(text[1:]) if int(text[1:]) < 90 else 1900 + int(text[1:])
            return cls(start_year=start, end_year=start + 3)
        start_text, _, end_text = text.partition("-")
        if not end_text:
            raise ValueError(f"cannot parse study period from {value!r}")
        return cls(start_year=int(start_text), end_year=int(end_text))

    @property
    def code(self) -> str:
        """The DMS code for this period, e.g. ``T25``."""
        return f"T{self.start_year % 100:02d}"

    @property
    def short_code(self) -> str:
        """The two-digit start year used inside DMS download paths, e.g. ``25``."""
        return f"{self.start_year % 100:02d}"

    @property
    def label(self) -> str:
        """The human readable period, e.g. ``2025-2028``."""
        return f"{self.start_year}-{self.end_year}"


class MeetingId(BaseModel):
    """Identifies an ITU-T meeting by its start date."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date | None = None

    @classmethod
    def from_code(cls, code: str) -> MeetingId:
        """Parse a DMS meeting code such as ``261015``."""
        text = code.strip()
        if not (len(text) == 6 and text.isdigit()):
            raise ValueError(f"cannot parse meeting code from {code!r}")
        return cls(start_date=date(2000 + int(text[:2]), int(text[2:4]), int(text[4:])))

    @property
    def code(self) -> str:
        """The DMS code for this meeting, e.g. ``261015``."""
        return self.start_date.strftime("%y%m%d")

    @property
    def label(self) -> str:
        """The human readable meeting date, e.g. ``2026-10-15``."""
        return self.start_date.isoformat()


class DocumentRef(BaseModel):
    """The identity of a single ITU-T document."""

    model_config = ConfigDict(frozen=True)

    study_period: StudyPeriod
    study_group: int = Field(ge=1, le=99)
    doc_type: DocType
    number: int = Field(ge=0)
    subtype: str | None = None
    meeting: MeetingId | None = None

    @classmethod
    def parse(cls, document_id: str) -> DocumentRef:
        """Parse a DMS document identifier such as ``T25-SG12-261015-TD-GEN-0520``."""
        match = _DOCUMENT_ID_RE.match(document_id.strip())
        if match is None:
            raise ValueError(f"cannot parse document identifier from {document_id!r}")
        period = StudyPeriod(start_year=2000 + int(match["period"]), end_year=2000 + int(match["period"]) + 3)
        meeting = MeetingId.from_code(match["meeting"]) if match["meeting"] else None
        return cls(
            study_period=period,
            study_group=int(match["group"]),
            doc_type=DocType(match["type"]),
            number=int(match["number"]),
            subtype=match["subtype"],
            meeting=meeting,
        )

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
        return f"https://www.itu.int{path}/{self.document_id}{marker}{file_format.value}-{language.value}.{suffix}"

    def detail_url(self) -> str:
        """Build the URL of the DMS detail page for this document."""
        return f"https://www.itu.int/md/meetingdoc.asp?lang=en&parent={self.document_id}"


class DocumentFile(BaseModel):
    """One downloadable rendition of a document."""

    model_config = ConfigDict(frozen=True)

    format_code: str
    language_code: str
    size_bytes: int | None = None
    posted: date | None = None
    url: str
    revision: int | None = None

    @property
    def file_format(self) -> DocFormat | None:
        """The parsed format code, or ``None`` when the DMS uses an unknown code."""
        return DocFormat.parse(self.format_code)

    @property
    def language(self) -> DocLanguage | None:
        """The parsed language code, or ``None`` when the DMS uses an unknown code."""
        return DocLanguage.parse(self.language_code)

    @property
    def extension(self) -> str:
        """The file name extension of the rendition.

        The DMS publishes a document in the format it was submitted in, so the
        extension of the download URL is the authoritative one and the default
        of the format is only used as a fallback.
        """
        match = _EXTENSION_RE.search(urlsplit(self.url).path.rsplit("/", maxsplit=1)[-1])
        if match is not None:
            return match.group("extension").lower()
        file_format = self.file_format
        if file_format is None:
            return ""
        return default_extension(file_format)


class DocumentMetadata(BaseModel):
    """Metadata scraped for a document from the ITU-T DMS listing and detail pages."""

    ref: DocumentRef
    title: str = ""
    sources: list[str] = Field(default_factory=list)
    questions: list[int] = Field(default_factory=list)
    posted: date | None = None
    revision: int | None = None
    files: list[DocumentFile] = Field(default_factory=list)
    detail_url: str = ""
    summary: str | None = None

    @property
    def document_id(self) -> str:
        """The DMS identifier of the described document."""
        return self.ref.document_id
