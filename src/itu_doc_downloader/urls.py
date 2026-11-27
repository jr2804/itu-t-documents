"""URL builders for the ITU-T document management system.

All ITU-T document pages live under ``https://www.itu.int``. The meeting
document application (``meetingdoc.asp``) is addressed by a ``parent``
parameter that identifies the meeting and the document type.
"""

from __future__ import annotations

from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType

#: Root of the ITU-T web site.
BASE_URL = "https://www.itu.int"

#: The meeting document application.
MEETING_DOC_URL = f"{BASE_URL}/md/meetingdoc.asp"

#: Language of the scraped pages.
LANGUAGE = "en"

#: Mapping of ITU-T study periods to the index used by the ``net4`` web apps.
PERIOD_INDICES: dict[str, int] = {
    "2005-2008": 13,
    "2009-2012": 14,
    "2013-2016": 15,
    "2017-2020": 16,
    "2022-2024": 17,
    "2025-2028": 18,
}


def period_index(period: StudyPeriod) -> int:
    """Return the ``net4`` web application index of a study period.

    Args:
        period: The study period.

    Returns:
        The index used by ``loqr.aspx`` and ``sgstructure.aspx``.

    Raises:
        KeyError: When the period is not known to the web applications.
    """
    return PERIOD_INDICES[period.label]


def study_group_page_url(period: StudyPeriod, study_group: int) -> str:
    """Return the URL of the study group home page.

    Args:
        period: The study period.
        study_group: The study group number.

    Returns:
        The absolute URL of the study group page.
    """
    return f"{BASE_URL}/en/ITU-T/studygroups/{period.label}/{study_group:02d}/Pages/default.aspx"


def questions_url(study_group: int, index: int) -> str:
    """Return the URL of the "List of Questions and Rapporteurs" page.

    Args:
        study_group: The study group number.
        index: The ``net4`` study period index.

    Returns:
        The absolute URL of the questions page.
    """
    return f"{BASE_URL}/net4/ITU-T/lists/loqr.aspx?Group={study_group}&Period={index}"


def structure_url(study_group: int, index: int) -> str:
    """Return the URL of the "Structure" page of a study group.

    Args:
        study_group: The study group number.
        index: The ``net4`` study period index.

    Returns:
        The absolute URL of the structure page.
    """
    return f"{BASE_URL}/net4/ITU-T/lists/sgstructure.aspx?Group={study_group}&Period={index}"


def meeting_summary_url(period: StudyPeriod, study_group: int, meeting: MeetingId) -> str:
    """Return the URL of the summary page of a meeting.

    Args:
        period: The study period.
        study_group: The study group number.
        meeting: The meeting.

    Returns:
        The absolute URL of the meeting summary page.
    """
    return f"{BASE_URL}/md/{period.code}-SG{study_group:02d}-{meeting.code}/sum/en"


def listing_url(
    period: StudyPeriod,
    study_group: int,
    doc_type: DocType,
    meeting: MeetingId | None = None,
    subtype: str | None = None,
) -> str:
    """Return the URL of a document listing.

    Contributions and temporary documents are listed per meeting, collective
    letters and reports are listed per study period. The aggregate listing of
    the temporary documents of a meeting only shows a preview of five
    documents per sub-type, so the full listing is addressed by the sub-type.

    Args:
        period: The study period.
        study_group: The study group number.
        doc_type: The document type to list.
        meeting: The meeting to list documents for.
        subtype: The sub-type of the temporary documents to list, e.g. ``GEN``.

    Returns:
        The absolute URL of the listing page.
    """
    parts = [period.code, f"SG{study_group:02d}"]
    if meeting is not None:
        parts.append(meeting.code)
    parts.append(doc_type.value)
    if subtype is not None:
        parts.append(subtype)
    return f"{MEETING_DOC_URL}?lang={LANGUAGE}&parent={'-'.join(parts)}"


def detail_url(document_id: str) -> str:
    """Return the URL of the detail page of a document.

    Args:
        document_id: The DMS identifier of the document.

    Returns:
        The absolute URL of the detail page.
    """
    return f"{MEETING_DOC_URL}?lang={LANGUAGE}&parent={document_id}"


def detail_url_for(ref: DocumentRef) -> str:
    """Return the URL of the detail page of a document.

    Args:
        ref: The identity of the document.

    Returns:
        The absolute URL of the detail page.
    """
    return detail_url(ref.document_id)
