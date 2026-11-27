"""Tests for the command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import get_args, get_type_hints

import pytest

from itu_t_documents.catalogue import CatalogueEntry
from itu_t_documents.cli import commands
from itu_t_documents.errors import AccessDeniedError, AuthenticationError, IncompleteListingError, UnknownEntityError
from itu_t_documents.models.catalogue import StructureGroup, StudyGroup, StudyGroupStructure
from itu_t_documents.models.documents import MeetingId
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.questions import Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


class FakeMeeting:
    """A meeting of the fake API."""

    def __init__(self, code: str, place: str) -> None:
        """Create the fake meeting."""
        self.code = code
        self.place = place
        self.label = f"{place} ({code})"


class FakeCatalogue:
    """The catalogue of the fake API."""

    def __init__(self) -> None:
        """Create the fake catalogue."""
        self.empty = False

    def study_groups(self, period: StudyPeriod) -> list[StudyGroup]:
        """Return the study groups of the period."""
        if self.empty:
            return []
        return [StudyGroup(number=number, period=period) for number in (12, 21)]

    def structure(self, study_group: int, period: StudyPeriod) -> StudyGroupStructure:
        """Return the structure of the study group."""
        if study_group != 12:
            raise UnknownEntityError(f"{period.label} has no study group SG{study_group:02d}")
        group = StudyGroup(number=study_group, period=period)
        return StudyGroupStructure(
            study_group=group,
            plenary=WorkingGroup(code="PLEN", name="PLEN"),
            working_groups=[WorkingGroup(code="WP1/12", name="WP1 12")],
            questions=[
                Question(
                    number=15,
                    study_group=study_group,
                    title="Parametric and E-model-based planning",
                    working_group=WorkingGroup(code="WP1/12", name="WP1 12"),
                )
            ],
            other_groups=[StructureGroup(code="SG12RG-AFR", title="Regional Group for Africa", kind="regional")],
        )

    def search(self, text: str, period: StudyPeriod | None = None) -> list[CatalogueEntry]:
        """Return the entries that mention the text."""
        if "speech" not in text:
            return []
        return [CatalogueEntry(kind="question", code="Q15/12", title="speech", study_group=12, period="2025-2028")]


class FakeStore:
    """The store of the fake API."""

    database_path = Path("/tmp/metadata.db")


class FakeApi:
    """A stand-in for the API that records the calls it receives."""

    def __init__(self) -> None:
        """Create the fake API."""
        self.store = FakeStore()
        self.calls: list[tuple] = []
        self.truncated = False
        self.catalogue = FakeCatalogue()

    def __enter__(self) -> FakeApi:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def close(self) -> None:
        """Close the fake API."""

    def list_meetings(self, study_group: int, study_period: StudyPeriod) -> list[FakeMeeting]:
        """Return the meetings of the fake study group."""
        self.calls.append(("list_meetings", study_group, study_period))
        return [FakeMeeting("270119", "Geneva"), FakeMeeting("261015", "E-Meeting")]

    def list_questions(self, study_group: int, study_period: StudyPeriod) -> list:
        """Return the questions of the fake study group."""
        self.calls.append(("list_questions", study_group, study_period))
        return []

    def sync_meeting(self, study_group: int, meeting: MeetingId, study_period: StudyPeriod, doc_types=()) -> int:
        """Store the documents of a meeting."""
        self.calls.append(("sync_meeting", study_group, meeting.code))
        if self.truncated:
            raise IncompleteListingError("the listing holds 3 of 85 documents")
        return 7

    def find_documents(self, **kwargs) -> list:
        """Return the documents of the fake study group."""
        self.calls.append(("find_documents", kwargs))
        return []


class RefusingApi:
    """A stand-in for the API whose download fails with a given error."""

    def __init__(self, error: Exception) -> None:
        """Keep the error that the download raises."""
        self.error = error

    def download(self, ref, file_format, language, output=None) -> Path:
        """Refuse the download."""
        raise self.error

    def __enter__(self) -> RefusingApi:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _SettingsWithoutCredentials:
    """Settings without any credentials."""

    config_file = Path("~/.config/itu-t-documents/config.toml")

    def has_credentials(self) -> bool:
        """Report that no credentials are available."""
        return False


def test_meetings_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The meetings command lists the meetings of a study group."""
    commands.meetings(study_group=12, study_period="2025-2028")

    out = capsys.readouterr().out
    assert "270119" in out
    assert "261015" in out
    assert ("list_meetings", 12, PERIOD) in fake_api.calls


def test_meetings_command_with_an_empty_period(fake_api: FakeApi) -> None:
    """An empty period, as an empty environment variable leaves it, means the current one."""
    commands.meetings(study_group=12, study_period="")

    assert ("list_meetings", 12, StudyPeriod.current()) in fake_api.calls


def test_questions_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The questions command lists the questions of a study group."""
    commands.questions(study_group=12, study_period="2025-2028")

    assert ("list_questions", 12, PERIOD) in fake_api.calls


def test_sync_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The sync command stores the documents of a meeting."""
    commands.sync(study_group=12, study_period="2025-2028", meeting="260609")

    out = capsys.readouterr().out
    assert "260609: 7 documents" in out
    assert ("sync_meeting", 12, "260609") in fake_api.calls


def test_sync_command_without_a_meeting(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """Without a meeting every meeting of the study group is synchronised."""
    commands.sync(study_group=12, study_period="2025-2028", meeting=None)

    out = capsys.readouterr().out
    assert "270119: 7 documents" in out
    assert "261015: 7 documents" in out


def test_sync_command_with_an_incomplete_listing(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """A truncated listing is reported instead of storing incomplete data."""
    fake_api.truncated = True

    commands.sync(study_group=12, study_period="2025-2028", meeting="260609")

    out = capsys.readouterr().out
    assert "the listing is incomplete" in out
    assert "3 of 85" in out


def test_documents_command_without_results(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """Without results the documents command explains what to do."""
    commands.documents(study_group=12, study_period="2025-2028")

    assert "No documents found" in capsys.readouterr().out


def test_documents_command_with_a_type(fake_api: FakeApi) -> None:
    """The documents command passes the document type and period on."""
    commands.documents(study_group=12, study_period="2025-2028", doc_type="TD")

    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["doc_type"] is DocType.TEMPORARY_DOCUMENT
    assert call[1]["study_period"] == "2025-2028"


def test_documents_command_without_a_period(fake_api: FakeApi) -> None:
    """Without a period the documents command searches all periods."""
    commands.documents(study_group=12)

    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["study_period"] is None


def test_documents_command_with_an_empty_period(fake_api: FakeApi) -> None:
    """An empty period, as an empty environment variable leaves it, means every period."""
    commands.documents(study_group=12, study_period="")

    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["study_period"] is None


def test_documents_command_searches_every_period_by_default() -> None:
    """The help of the documents command promises every period, not the current one."""
    hints = get_type_hints(commands.documents, include_extras=True)

    assert "Defaults to every study period." in get_args(hints["study_period"])[1].help


def test_auth_command_without_credentials(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Without credentials the auth command explains what to set."""
    monkeypatch.setattr(commands, "Settings", _SettingsWithoutCredentials)

    commands.auth()

    out = capsys.readouterr().out
    assert "No TIES credentials found" in out
    assert "ITU_TIES_USERNAME" in out


def test_download_command_with_an_invalid_identifier(capsys: pytest.CaptureFixture[str]) -> None:
    """The download command reports an identifier it cannot read."""
    commands.download("nonsense", file_format="PDF", language="E")

    assert "Not a document identifier" in capsys.readouterr().out


def test_download_command_with_an_unavailable_rendition(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports a rendition the ITU-T does not offer."""
    error = FileNotFoundError("T25-SG12-C-0192 is not available")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    commands.download("T25-SG12-C-0192", file_format="PDF", language="E")

    out = capsys.readouterr().out
    assert "is not available as PDF-E" in out


def test_download_command_with_a_document_the_account_may_not_see(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports a document outside the membership."""
    error = AccessDeniedError("T25-SG13-C-0001 is not accessible with these credentials")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    commands.download("T25-SG13-C-0001", file_format="PDF", language="E")

    out = capsys.readouterr().out
    assert "is not accessible with these credentials" in out
    assert "membership" in out


def test_download_command_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports missing credentials instead of crashing."""
    error = AuthenticationError("no TIES credentials configured; set ITU_TIES_USERNAME and ITU_TIES_PASSWORD")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    commands.download("T25-SG12-COL-0001", file_format="MSW", language="F")

    out = capsys.readouterr().out
    assert "no TIES credentials configured" in out
    assert "ITU_TIES_USERNAME" in out


# ----------------------------------------------------------------------
# The catalogue of the ITU-T study groups
# ----------------------------------------------------------------------


def test_periods_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The periods command lists the study periods of the ITU-T."""
    commands.periods()

    out = capsys.readouterr().out
    assert "2025-2028" in out
    assert "(current)" in out


def test_study_groups_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The study groups command lists the study groups of a period."""
    commands.study_groups(study_period="2025-2028")

    out = capsys.readouterr().out
    assert "SG12" in out
    assert "SG21" in out


def test_structure_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The structure command shows the groups of a study group."""
    commands.structure(study_group=12, study_period="2025-2028")

    out = capsys.readouterr().out
    assert "WP1/12" in out
    assert "Q15/12" in out
    assert "SG12RG-AFR" in out


def test_study_groups_command_without_a_study_group(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The study groups command reports a period without study groups."""
    fake_api.catalogue.empty = True

    commands.study_groups(study_period="2025-2028")

    assert "publishes no study group" in capsys.readouterr().out


def test_structure_command_with_an_unknown_study_group(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The structure command reports a study group that does not exist."""
    commands.structure(study_group=9, study_period="2025-2028")

    assert "has no study group SG09" in capsys.readouterr().out


def test_search_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The search command finds the groups that mention the text."""
    commands.search("speech", study_period="2025-2028")

    out = capsys.readouterr().out
    assert "Q15/12" in out


def test_search_command_without_a_match(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The search command reports that nothing matches."""
    commands.search("nothing-at-all", study_period="2025-2028")

    assert "Nothing in 2025-2028" in capsys.readouterr().out


def test_search_command_defaults_to_the_current_period(
    monkeypatch: pytest.MonkeyPatch,
    fake_api: FakeApi,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without an explicit period the search uses the current study period."""
    monkeypatch.setattr(StudyPeriod, "current", staticmethod(lambda: PERIOD))

    commands.search("nothing-at-all")

    assert "Nothing in 2025-2028" in capsys.readouterr().out


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    """Replace the API used by the CLI commands."""
    api = FakeApi()
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: api)
    return api
