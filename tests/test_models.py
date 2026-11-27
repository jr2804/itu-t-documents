"""Tests for the domain model of ITU-T meeting documents."""

from __future__ import annotations

from datetime import date

import pytest

from itu_t_documents.models.catalogue import StudyGroup
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType, Role
from itu_t_documents.models.metadata import DocumentFile
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.urls import detail_url_for

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


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


def test_single_digit_study_groups_are_zero_padded() -> None:
    """The ITU-T writes study group 5 as ``SG05``."""
    ref = DocumentRef(
        study_period=StudyPeriod(start_year=2025, end_year=2028),
        study_group=5,
        doc_type=DocType.CONTRIBUTION,
        number=538,
    )

    assert ref.study_group_code == "SG05"
    assert ref.document_id == "T25-SG05-C-0538"
    assert ref.download_url(DocFormat.WORD, DocLanguage.ENGLISH) == ("https://www.itu.int/dms_ties/itu-t/md/25/sg05/c/T25-SG05-C-0538!!MSW-E.docx")


def test_document_ref_rejects_garbage() -> None:
    """An unparsable document identifier is rejected."""
    with pytest.raises(ValueError):
        DocumentRef.parse("not-a-document")


def test_document_ref_parses_a_document_of_the_renamed_study_period() -> None:
    """The period code of the identifier names the first year of the period.

    The 2022-2024 period is the one that does not span four years, so the end
    year cannot be derived from the start year.
    """
    ref = DocumentRef.parse("T22-SG12-C-0192")

    assert ref.study_period.label == "2022-2024"
    assert ref.document_id == "T22-SG12-C-0192"


def test_document_ref_rejects_an_unknown_study_period() -> None:
    """A period code that names no study period is refused."""
    with pytest.raises(ValueError, match="no study period starting in 2021"):
        DocumentRef.parse("T21-SG12-C-0192")


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


def test_download_url_of_a_revision() -> None:
    """A revision is marked in the download URL."""
    ref = DocumentRef.parse("T25-SG02-C-0001")

    url = ref.download_url(DocFormat.WORD, DocLanguage.ENGLISH, revision=1)

    assert url == "https://www.itu.int/dms_ties/itu-t/md/25/sg02/c/T25-SG02-C-0001!R1!MSW-E.docx"


def test_download_url_with_an_explicit_extension() -> None:
    """The extension of a document may differ from the default of its format."""
    ref = DocumentRef.parse("T25-SG13-R-0001")

    url = ref.download_url(DocFormat.WORD, DocLanguage.ENGLISH, extension="doc")

    assert url == "https://www.itu.int/dms_ties/itu-t/md/25/sg13/r/T25-SG13-R-0001!!MSW-E.doc"


def test_document_file_uses_the_extension_of_its_url() -> None:
    """The extension of a rendition follows its download URL."""
    rendition = DocumentFile(
        format_code="MSW",
        language_code="E",
        url="https://www.itu.int/dms_ties/itu-t/md/25/sg13/r/T25-SG13-R-0001!!MSW-E.doc",
    )

    assert rendition.extension == "doc"


def test_a_study_period_is_built_from_its_start_year() -> None:
    """A study period is named by the year it starts in."""
    period = StudyPeriod.from_year(2025)

    assert period.label == "2025-2028"
    assert period.code == "T25"


def test_a_study_period_of_an_unknown_year_is_refused() -> None:
    """A year that starts no study period is refused."""
    with pytest.raises(ValueError, match="2021"):
        StudyPeriod.from_year(2021)


def test_the_year_of_a_study_period_is_found() -> None:
    """The study period a year falls into is found."""
    assert StudyPeriod.containing(2026).label == "2025-2028"
    assert StudyPeriod.containing(2007).label == "2005-2008"


def test_a_year_without_a_study_period_is_refused() -> None:
    """A year that falls into no study period is refused."""
    with pytest.raises(ValueError, match="2021"):
        StudyPeriod.containing(2021)


def test_a_study_period_that_does_not_exist_is_refused() -> None:
    """A period the ITU-T does not know cannot be constructed."""
    with pytest.raises(ValueError, match="2030-2033"):
        StudyPeriod(start_year=2030, end_year=2033)


def test_the_known_study_periods_are_listed() -> None:
    """The catalogue of the study periods holds every period of the ITU-T."""
    labels = [period.label for period in StudyPeriod.all()]

    assert labels[0] == "2005-2008"
    assert labels[-1] == "2029-2032"
    assert "2025-2028" in labels


def test_a_study_period_is_parsed_from_a_year() -> None:
    """A study period is parsed from a label, a code or a year."""
    assert StudyPeriod.parse("2025-2028") == StudyPeriod.from_year(2025)
    assert StudyPeriod.parse("T25") == StudyPeriod.from_year(2025)
    assert StudyPeriod.parse("2025") == StudyPeriod.from_year(2025)


def test_a_study_group_carries_its_period() -> None:
    """A study group is named by its number and its period."""
    group = StudyGroup(number=5, period=StudyPeriod.from_year(2025))

    assert group.code == "SG05"
    assert group.label == "SG05 (2025-2028)"


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


def test_meeting_id_rejects_an_invalid_code() -> None:
    """A meeting code that is not a date is rejected."""
    with pytest.raises(ValueError):
        MeetingId.from_code("26101")


def test_meeting_id_label() -> None:
    """The label of a meeting is its start date."""
    assert MeetingId.from_code("261015").label == "2026-10-15"


def test_document_ref_detail_url() -> None:
    """The detail page of a document is addressed by its identifier."""
    ref = DocumentRef.parse("T25-SG12-C-0192")

    assert ref.detail_url() == "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-C-0192"
    assert detail_url_for(ref) == ref.detail_url()


def test_document_ref_visibility() -> None:
    """Every document type has an access level."""
    assert DocumentRef.parse("T25-SG12-C-0192").visibility.value == "ties"
    assert DocumentRef.parse("T25-SG12-COL-0001").visibility.value == "pub"
    assert DocumentRef.parse("T25-SG12-R-0001").visibility.value == "ties"
    assert DocumentRef.parse("T25-SG12-261015-TD-GEN-0520").visibility.value == "inf"


def test_document_file_extension() -> None:
    """The extension of a rendition follows its format."""
    assert DocumentFile(format_code="MSW", language_code="E", url="u").extension == "docx"
    assert DocumentFile(format_code="PDF", language_code="E", url="u").extension == "pdf"
    assert DocumentFile(format_code="ZIP", language_code="E", url="u").extension == "zip"
    assert DocumentFile(format_code="HTM", language_code="E", url="u").extension == "htm"


def test_study_period_rejects_a_reversed_period() -> None:
    """A period that ends before it starts is rejected."""
    with pytest.raises(ValueError):
        StudyPeriod(start_year=2028, end_year=2025)


def test_document_ref_of_a_temporary_document_without_a_subtype() -> None:
    """A temporary document without a sub-type uses the general one."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=1,
        meeting=MeetingId.from_code("261015"),
    )

    assert ref.document_id == "T25-SG12-261015-TD-GEN-0001"


def test_document_ref_of_a_temporary_document_without_a_meeting() -> None:
    """A temporary document without a meeting has no download URL."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=1,
    )

    with pytest.raises(ValueError):
        _ = ref.download_url(DocFormat.PDF, DocLanguage.ENGLISH)


def test_document_file_without_a_known_format() -> None:
    """A file with an unknown format code has no extension."""
    rendition = DocumentFile(format_code="XYZ", language_code="Q", url="https://example.org")

    assert rendition.file_format is None
    assert rendition.language is None
    assert rendition.extension == ""
