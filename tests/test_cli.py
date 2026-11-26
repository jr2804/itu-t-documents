"""Tests for the command line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_doc_downloader.cli import commands
from itu_doc_downloader.models.documents import MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocType

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


class FakeMeeting:
    """A meeting of the fake API."""

    def __init__(self, code: str, place: str) -> None:
        """Create the fake meeting."""
        self.code = code
        self.place = place
        self.label = f"{place} ({code})"


class FakeStore:
    """The store of the fake API."""

    database_path = Path("/tmp/metadata.db")


class FakeApi:
    """A stand-in for the API that records the calls it receives."""

    def __init__(self) -> None:
        """Create the fake API."""
        self.store = FakeStore()
        self.calls: list[tuple] = []

    def __enter__(self) -> FakeApi:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def close(self) -> None:
        """Close the fake API."""

    def list_meetings(self, study_group: int, study_period: StudyPeriod) -> list[FakeMeeting]:
        """Return the meetings of the fake study group."""
        self.calls.append(("list_meetings", study_group))
        return [FakeMeeting("270119", "Geneva"), FakeMeeting("261015", "E-Meeting")]

    def list_questions(self, study_group: int, study_period: StudyPeriod) -> list:
        """Return the questions of the fake study group."""
        self.calls.append(("list_questions", study_group))
        return []

    def sync_meeting(self, study_group: int, meeting: MeetingId, study_period: StudyPeriod, doc_types=()) -> int:
        """Store the documents of a meeting."""
        self.calls.append(("sync_meeting", study_group, meeting.code))
        return 7

    def find_documents(self, **kwargs) -> list:
        """Return the documents of the fake study group."""
        self.calls.append(("find_documents", kwargs))
        return []


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    """Replace the API used by the CLI commands."""
    api = FakeApi()
    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: api)
    return api


def test_meetings_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The meetings command lists the meetings of a study group."""
    commands.meetings(study_group=12, study_period="2025-2028")

    out = capsys.readouterr().out
    assert "270119" in out
    assert "261015" in out
    assert ("list_meetings", 12) in fake_api.calls


def test_questions_command(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """The questions command lists the questions of a study group."""
    commands.questions(study_group=12, study_period="2025-2028")

    assert ("list_questions", 12) in fake_api.calls


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


def test_documents_command_without_results(fake_api: FakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    """Without results the documents command explains what to do."""
    commands.documents(study_group=12, study_period="2025-2028")

    assert "No documents found" in capsys.readouterr().out


def test_documents_command_with_a_type(fake_api: FakeApi) -> None:
    """The documents command passes the document type on."""
    commands.documents(study_group=12, study_period="2025-2028", doc_type="TD")

    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["doc_type"] is DocType.TEMPORARY_DOCUMENT


def test_auth_command_without_credentials(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Without credentials the auth command explains what to set."""
    monkeypatch.setattr(commands, "Settings", _SettingsWithoutCredentials)

    commands.auth()

    out = capsys.readouterr().out
    assert "No TIES credentials found" in out
    assert "ITU_TIES_USERNAME" in out


class _SettingsWithoutCredentials:
    """Settings without any credentials."""

    config_file = Path("~/.config/itu-doc-downloader/config.toml")

    def has_credentials(self) -> bool:
        """Report that no credentials are available."""
        return False


def test_download_command_with_an_invalid_identifier(capsys: pytest.CaptureFixture[str]) -> None:
    """The download command reports an identifier it cannot read."""
    commands.download("nonsense", file_format="PDF", language="E")

    assert "Not a document identifier" in capsys.readouterr().out


def test_download_command_with_an_unavailable_rendition(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The download command reports a rendition the ITU-T does not offer."""
    from itu_doc_downloader.cli import commands

    class FakeApi:
        """A stand-in for the API."""

        def download(self, ref, file_format, language, output=None) -> Path:
            """Refuse the download."""
            raise FileNotFoundError(f"{ref.document_id} is not available")

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def close(self) -> None:
            """Close the fake API."""

    monkeypatch.setattr(commands, "ItuDocuments", lambda *args, **kwargs: FakeApi())

    commands.download("T25-SG12-C-0192", file_format="PDF", language="E")

    out = capsys.readouterr().out
    assert "is not available as PDF-E" in out
