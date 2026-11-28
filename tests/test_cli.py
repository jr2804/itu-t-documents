"""Tests for the command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import get_args, get_type_hints

import httpx
import pytest

from itu_t_documents.api import SyncReport
from itu_t_documents.catalogue import CatalogueEntry
from itu_t_documents.cli import commands, startup
from itu_t_documents.cli.app import ItuApp
from itu_t_documents.cli.app import app as cli_app
from itu_t_documents.errors import AccessDeniedError, AuthenticationError, IncompleteListingError, UnknownEntityError
from itu_t_documents.models.catalogue import StructureGroup, StudyGroup, StudyGroupStructure
from itu_t_documents.models.documents import MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType, Role
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.storage.queries import DocumentRecord, SourceCount

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

    def sync_study_group(self, study_group: int, study_period: StudyPeriod, doc_types=()) -> SyncReport:
        """Store the documents of a study group."""
        self.calls.append(("sync_study_group", study_group))
        if self.truncated:
            raise IncompleteListingError("the listing holds 3 of 85 documents")
        return SyncReport(meetings=(("270119", 7), ("261015", 7)), period_only=2)

    def count_documents(self) -> int:
        """Return the number of stored documents."""
        return 0

    def find_documents(self, **kwargs) -> list:
        """Return the documents of the fake study group."""
        self.calls.append(("find_documents", kwargs))
        return []

    def top_sources(self, study_group: int, *, last_meetings=None, study_period=None, limit=10) -> list[SourceCount]:
        """Return the most prolific sources."""
        self.calls.append(("top_sources", study_group, last_meetings, study_period, limit))
        return [SourceCount(source="ITU-T Study Group 12", count=19, contributions=0, temporary_documents=19)]


class RefusingApi:
    """A stand-in for the API whose download fails with a given error."""

    def __init__(self, error: Exception) -> None:
        """Keep the error that the download raises."""
        self.error = error

    def download(self, ref, file_format, language, output_file=None) -> Path:
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


def test_the_default_command_names_the_documentation(capsys: pytest.CaptureFixture[str]) -> None:
    """The default command introduces the package and where its documentation lives."""
    startup.default()

    out = capsys.readouterr().out
    assert "itu-t-documents" in out
    assert "https://jr2804.github.io/itu-t-documents/" in out


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
    assert "the period listing: 2 documents" in out
    assert ("sync_study_group", 12) in fake_api.calls


def test_sync_command_with_an_incomplete_listing(fake_api: FakeApi) -> None:
    """A truncated listing is reported instead of storing incomplete data."""
    fake_api.truncated = True

    with pytest.raises(IncompleteListingError, match="3 of 85"):
        commands.sync(study_group=12, study_period="2025-2028", meeting="260609")


def test_documents_command_without_results(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """Without results the documents command explains what to do."""
    commands.documents(study_group=12, study_period="2025-2028")

    assert "No documents found" in capsys.readouterr().out


def test_documents_command_with_a_type(fake_api: FakeApi) -> None:
    """The documents command passes the document type and period on."""
    commands.documents(study_group=12, study_period="2025-2028", doc_type=DocType.TEMPORARY_DOCUMENT)

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


def test_auth_command_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without credentials the auth command explains what to set."""
    monkeypatch.setattr(startup, "Settings", _SettingsWithoutCredentials)

    with pytest.raises(AuthenticationError, match="ITU_TIES_USERNAME"):
        commands.auth()


def test_top_sources_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The top-sources command counts the most recent stored meetings."""
    commands.top_sources(study_group=12, last_meetings=3, study_period="2025-2028", limit=5)

    assert "    19  ITU-T Study Group 12" in capsys.readouterr().out
    assert ("top_sources", 12, 3, PERIOD, 5) in fake_api.calls


def test_top_sources_command_without_results(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """Without stored documents the command explains what to do."""
    fake_api.top_sources = lambda *args, **kwargs: []
    commands.top_sources(study_group=12)

    assert "No documents found" in capsys.readouterr().out


def test_download_command_with_an_invalid_identifier(capsys: pytest.CaptureFixture[str]) -> None:
    """The download command reports an identifier it cannot read."""
    with pytest.raises(SystemExit) as stopped:
        cli_app(["download", "nonsense"])

    assert stopped.value.code == 1
    assert "cannot parse document identifier" in capsys.readouterr().err


def test_an_enum_option_converts_the_dms_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A value that cyclopts accepts becomes the enumeration member."""
    calls: list[tuple] = []

    class ReturningApi:
        def download(self, ref, file_format, language, output_file=None) -> Path:
            calls.append((ref.document_id, file_format, language))
            path = tmp_path / "contribution.docx"
            path.write_bytes(b"document")
            return path

        def __enter__(self) -> ReturningApi:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: ReturningApi())

    with pytest.raises(SystemExit) as stopped:
        cli_app(["download", "T25-SG12-C-0192", "--format", "MSW"])

    assert stopped.value.code == 0
    assert calls == [("T25-SG12-C-0192", DocFormat.WORD, DocLanguage.ENGLISH)]


def test_the_cli_reports_an_unreachable_site(capsys: pytest.CaptureFixture[str]) -> None:
    """A connection failure is one line on stderr and exit code 1."""
    app = ItuApp(name="test")

    def unreachable() -> None:
        raise httpx.ConnectError("offline")

    app.command(unreachable)
    with pytest.raises(SystemExit) as stopped:
        app(["unreachable"])

    assert stopped.value.code == 1
    assert "cannot reach the ITU-T: offline" in capsys.readouterr().err


def test_a_value_outside_the_choices_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Cyclopts rejects a format outside the enumeration before the command runs."""
    with pytest.raises(SystemExit) as stopped:
        cli_app(["download", "T25-SG12-C-0192", "--format", "nope"])

    assert stopped.value.code == 2
    assert "Invalid value" in capsys.readouterr().err


def test_download_command_with_an_unavailable_rendition(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports a rendition the ITU-T does not offer."""
    error = FileNotFoundError("T25-SG12-C-0192 is not available")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    with pytest.raises(FileNotFoundError, match="not available"):
        commands.download("T25-SG12-C-0192", file_format=DocFormat.PDF, language=DocLanguage.ENGLISH)


def test_download_command_with_a_document_the_account_may_not_see(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports a document outside the membership."""
    error = AccessDeniedError("T25-SG13-C-0001 is not accessible with these credentials")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    with pytest.raises(AccessDeniedError, match="not accessible"):
        commands.download("T25-SG13-C-0001", file_format=DocFormat.PDF, language=DocLanguage.ENGLISH)


def test_download_command_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports missing credentials instead of crashing."""
    error = AuthenticationError("no TIES credentials configured; set ITU_TIES_USERNAME and ITU_TIES_PASSWORD")
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: RefusingApi(error))

    with pytest.raises(AuthenticationError, match="ITU_TIES_USERNAME"):
        commands.download("T25-SG12-COL-0001", file_format=DocFormat.WORD, language=DocLanguage.FRENCH)


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


def test_structure_command_with_an_unknown_study_group(fake_api: FakeApi) -> None:
    """The structure command reports a study group that does not exist."""
    with pytest.raises(UnknownEntityError, match="has no study group SG09"):
        commands.structure(study_group=9, study_period="2025-2028")


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


def test_cli_mcp_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mcp command starts the MCP server."""
    started: list[bool] = []
    monkeypatch.setattr("itu_t_documents.mcp.main", lambda: started.append(True))

    commands.mcp()

    assert started == [True]


def test_cli_auth_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The auth command reports a successful login."""

    class FakeSettings:
        """Settings with credentials."""

        config_file = Path("~/.config/itu-t-documents/config.toml")

        def has_credentials(self) -> bool:
            """Report that credentials are available."""
            return True

    class FakeClient:
        """A client that authenticates."""

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def authenticate(self) -> None:
            """Authenticate successfully."""

    monkeypatch.setattr(startup, "Settings", FakeSettings)
    monkeypatch.setattr(startup, "ItuHttpClient", lambda settings: FakeClient())

    commands.auth()

    assert "TIES login succeeded" in capsys.readouterr().out


def test_cli_auth_command_reports_a_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The auth command reports a failed login."""

    class FakeSettings:
        """Settings with credentials."""

        config_file = Path("~/.config/itu-t-documents/config.toml")

        def has_credentials(self) -> bool:
            """Report that credentials are available."""
            return True

    class FakeClient:
        """A client whose login fails."""

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def authenticate(self) -> None:
            """Fail the login."""
            raise AuthenticationError("invalid credentials")

    monkeypatch.setattr(startup, "Settings", FakeSettings)
    monkeypatch.setattr(startup, "ItuHttpClient", lambda settings: FakeClient())

    with pytest.raises(AuthenticationError, match="invalid credentials"):
        commands.auth()

    assert capsys.readouterr().out == ""


def test_cli_questions_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The questions command lists the questions of a study group."""

    class FakeApi:
        """A stand-in for the API."""

        def list_questions(self, study_group: int, study_period) -> list[Question]:
            """Return one question."""
            return [
                Question(
                    number=5,
                    study_group=12,
                    title="Telephonometric methodologies",
                    working_group=WorkingGroup.parse("WP1/12"),
                    people=[Person(name="Lars Birger NIELSEN", role=Role.RAPPORTEUR)],
                )
            ]

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def close(self) -> None:
            """Close the fake API."""

    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: FakeApi())

    commands.questions(study_group=12, study_period="2025-2028")

    out = capsys.readouterr().out
    assert "Q5/12" in out
    assert "Lars Birger NIELSEN" in out


def test_cli_documents_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The documents command prints the documents it found."""

    class FakeApi:
        """A stand-in for the API."""

        def find_documents(self, **kwargs) -> list[DocumentRecord]:
            """Return one document."""
            return [
                DocumentRecord(
                    document_id="T25-SG12-C-0192",
                    doc_type=DocType.CONTRIBUTION,
                    number=192,
                    subtype=None,
                    title="A proposal",
                    sources=("Acme Ltd. (Germany)",),
                    questions=(5,),
                )
            ]

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def close(self) -> None:
            """Close the fake API."""

    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: FakeApi())

    commands.documents(study_group=12, study_period="2025-2028")

    out = capsys.readouterr().out
    assert "T25-SG12-C-0192" in out
    assert "Acme Ltd." in out


def test_cli_download_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The download command writes the document and reports its size."""

    class FakeApi:
        """A stand-in for the API."""

        def download(self, ref, file_format, language, output_file=None) -> Path:
            """Return the path of the downloaded document."""
            path = tmp_path / "document.pdf"
            path.write_bytes(b"content")
            return path

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def close(self) -> None:
            """Close the fake API."""

    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: FakeApi())

    commands.download("T25-SG12-C-0192", file_format=DocFormat.PDF, language=DocLanguage.ENGLISH)

    assert "7 bytes" in capsys.readouterr().out
