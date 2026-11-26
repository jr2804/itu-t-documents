"""Tests for the domain model of ITU-T meeting documents."""

from __future__ import annotations

from datetime import date

import pytest

from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType, Role
from itu_doc_downloader.models.questions import Person, Question, WorkingGroup


def test_study_period_from_label() -> None:
    """A study period is parsed from its label."""
    period = StudyPeriod.parse("2025-2028")

    assert period.start_year == 2025
    assert period.end_year == 2028
    assert period.label == "2025-2028"
    assert period.code == "T25"
    assert period.short_code == "25"


def test_study_period_from_code() -> None:
    """A study period is parsed from the DMS code."""
    period = StudyPeriod.parse("T25")

    assert period.start_year == 2025
    assert period.end_year == 2028


def test_study_period_rejects_unknown_format() -> None:
    """An unparsable study period is rejected."""
    with pytest.raises(ValueError):
        StudyPeriod.parse("nonsense")


def test_meeting_id_from_code() -> None:
    """A meeting is parsed from its DMS code."""
    meeting = MeetingId.from_code("261015")

    assert meeting.start_date == date(2026, 10, 15)
    assert meeting.code == "261015"


@pytest.mark.parametrize(
    ("document_id", "doc_type", "number", "subtype", "meeting"),
    [
        ("T25-SG12-C-0192", DocType.CONTRIBUTION, 192, None, None),
        ("T25-SG12-COL-0001", DocType.COLLECTIVE_LETTER, 1, None, None),
        ("T25-SG12-R-0001", DocType.REPORT, 1, None, None),
        ("T25-SG12-261015-TD-GEN-0520", DocType.TEMPORARY_DOCUMENT, 520, "GEN", "261015"),
    ],
)
def test_document_ref_round_trip(
    document_id: str,
    doc_type: DocType,
    number: int,
    subtype: str | None,
    meeting: str | None,
) -> None:
    """A parsed document identifier is rendered back unchanged."""
    ref = DocumentRef.parse(document_id)

    assert ref.doc_type is doc_type
    assert ref.number == number
    assert ref.subtype == subtype
    assert (ref.meeting.code if ref.meeting else None) == meeting
    assert ref.document_id == document_id


def test_document_ref_rejects_garbage() -> None:
    """An unparsable document identifier is rejected."""
    with pytest.raises(ValueError):
        DocumentRef.parse("not-a-document")


def test_contribution_identifier_has_no_meeting() -> None:
    """Contributions are numbered across the study period and carry no meeting."""
    period = StudyPeriod(start_year=2025, end_year=2028)
    ref = DocumentRef(
        study_period=period,
        study_group=12,
        doc_type=DocType.CONTRIBUTION,
        number=192,
    )

    assert ref.document_id == "T25-SG12-C-0192"
    assert ref.display_number == "192"


def test_temporary_document_identifier_carries_meeting_and_subtype() -> None:
    """Temporary documents embed the meeting and the sub-type."""
    period = StudyPeriod(start_year=2025, end_year=2028)
    ref = DocumentRef(
        study_period=period,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    assert ref.document_id == "T25-SG12-261015-TD-GEN-0520"
    assert ref.display_number == "520-GEN"


@pytest.mark.parametrize(
    ("document_id", "expected"),
    [
        (
            "T25-SG12-C-0192",
            "https://www.itu.int/dms_ties/itu-t/md/25/sg12/c/T25-SG12-C-0192!!MSW-E.docx",
        ),
        (
            "T25-SG12-261015-TD-GEN-0520",
            "https://www.itu.int/dms_inf/itu-t/md/25/sg12/td/261015/GEN/T25-SG12-261015-TD-GEN-0520!!PDF-E.pdf",
        ),
        (
            "T25-SG12-COL-0001",
            "https://www.itu.int/dms_pub/itu-t/md/25/sg12/col/T25-SG12-COL-0001!!MSW-E.docx",
        ),
        (
            "T25-SG12-R-0001",
            "https://www.itu.int/dms_ties/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx",
        ),
    ],
)
def test_download_url(document_id: str, expected: str) -> None:
    """The download URL follows the layout of the ITU-T document management system."""
    ref = DocumentRef.parse(document_id)

    url = ref.download_url(DocFormat.WORD if "MSW" in expected else DocFormat.PDF, DocLanguage.ENGLISH)

    assert url == expected


def test_temporary_document_requires_a_meeting() -> None:
    """A temporary document without a meeting cannot be addressed."""
    period = StudyPeriod(start_year=2025, end_year=2028)
    ref = DocumentRef(
        study_period=period,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=1,
    )

    with pytest.raises(ValueError):
        _ = ref.document_id


def test_working_group_parsing() -> None:
    """A working group code is parsed into its parts."""
    working_group = WorkingGroup.parse("WP1/12")

    assert working_group.code == "WP1/12"
    assert working_group.name == "WP1 12"
    assert not working_group.is_plenary
    assert WorkingGroup.parse("PLEN").is_plenary


def test_question_reports_its_roles() -> None:
    """A question lists the people holding a rapporteur role."""
    question = Question(
        number=5,
        study_group=12,
        title="Telephonometric methodologies",
        working_group=WorkingGroup.parse("WP1/12"),
        people=[
            Person(name="Lars Birger NIELSEN", role=Role.RAPPORTEUR),
            Person(name="Yiya HAO", role=Role.CO_RAPPORTEUR),
        ],
    )

    assert question.code == "Q5/12"
    assert [person.name for person in question.rapporteurs] == ["Lars Birger NIELSEN"]
    assert [person.name for person in question.co_rapporteurs] == ["Yiya HAO"]


def test_unknown_format_and_language_codes() -> None:
    """Unknown format and language codes are reported as unknown."""
    assert DocFormat.parse("XYZ") is None
    assert DocLanguage.parse("Q") is None
    assert DocFormat.parse("msw") is DocFormat.WORD
