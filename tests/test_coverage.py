"""Tests that cover the remaining branches of the package."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_t_documents.auth.ties import AuthenticationError
from itu_t_documents.cli import commands
from itu_t_documents.config.settings import Settings
from itu_t_documents.http.client import ItuHttpClient
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType, Role
from itu_t_documents.models.metadata import DocumentFile
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping import detail, listing, questions
from itu_t_documents.storage.files import FileCache
from itu_t_documents.storage.queries import DocumentRecord
from itu_t_documents.urls import detail_url_for

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


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


def test_parse_date_of_an_unreadable_value() -> None:
    """A date that cannot be read is reported as missing."""
    assert listing._parse_date("not a date") is None


def test_parse_listing_skips_a_row_without_an_identifier() -> None:
    """A row without a document identifier is ignored."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td><td>Q5/12</td><td>2026-05-27</td></tr></table></body></html>"
    )

    assert listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION) == []


def test_parse_listing_skips_a_row_with_an_unparsable_identifier() -> None:
    """A row with an unparsable document identifier is ignored."""
    page = (
        '<html><body><table><tr><td><input type="checkbox" id="nonsense" name="chkFile"/></td>'
        "<td>[ 1 ]</td><td>Title</td><td>Source</td><td>Q5/12</td><td>2026-05-27</td></tr></table></body></html>"
    )

    assert listing.parse_listing(page, PERIOD, 12, DocType.CONTRIBUTION) == []


def test_parse_other_meetings_skips_links_without_a_meeting() -> None:
    """Links that name no meeting are ignored."""
    page = '<html><body><td>Other Meetings : <a href="/md/meetingdoc.asp?lang=en&amp;parent=T25-SG12-C">x</a></td></body></html>'

    assert listing.parse_other_meetings(page) == []


def test_parse_meeting_header_without_a_place() -> None:
    """A header without a place yields no place."""
    page = "<html><body><p>Study Period 2025</p></body></html>"

    header = listing.parse_meeting_header(page)

    assert header == {"study_period": "2025"}


def test_parse_files_ignores_a_link_without_a_suffix() -> None:
    """A link that carries no format suffix is ignored."""
    page = '<html><body><table><tr><td><a href="/dms_inf/itu-t/md/x">Word</a></td></tr></table></body></html>'

    assert detail.parse_files(page) == []


def test_parse_size_of_an_unreadable_value() -> None:
    """A size that cannot be read is reported as missing."""
    assert detail._parse_size("unknown") is None


def test_parse_questions_skips_a_row_without_a_question_number() -> None:
    """A row whose question code cannot be read is ignored."""
    page = '<html><body><table><tr><td><span id="lblQWP_1">not a question</span></td><td></td></tr></table></body></html>'

    assert questions.parse_questions(page, 12) == []


def test_parse_questions_of_a_row_without_working_group() -> None:
    """A question without a working group falls back to the plenary."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12</span>'
        '<span id="lblQuestion_1">A question</span></td>'
        '<td><span id="lblFName_1">Ada</span><span id="lblLName_1">LOVELACE</span>'
        '<span id="lblRole_1">Rapporteur</span></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert parsed[0].working_group.code == "PLEN"


def test_file_cache_extensions(tmp_path: Path) -> None:
    """Every format has its own file extension."""
    cache = FileCache(Settings(cache_dir=tmp_path))
    ref = DocumentRef.parse("T25-SG12-C-0192")

    assert cache.path_for(ref, DocFormat.WORD, DocLanguage.ENGLISH).name == "MSW-E.docx"
    assert cache.path_for(ref, DocFormat.PDF, DocLanguage.FRENCH).name == "PDF-F.pdf"
    assert cache.path_for(ref, DocFormat.ZIP, DocLanguage.SPANISH).name == "ZIP-S.zip"
    assert cache.path_for(ref, DocFormat.HTML, DocLanguage.ENGLISH).name == "HTM-E.htm"


def test_http_client_authenticates(tmp_path: Path) -> None:
    """A login is performed when credentials are configured."""
    settings = Settings(cache_dir=tmp_path, ties_username="you@example.org", ties_password="secret")

    with ItuHttpClient(settings) as client:
        assert client.settings.has_credentials()


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

    monkeypatch.setattr(commands, "Settings", FakeSettings)
    monkeypatch.setattr(commands, "ItuHttpClient", lambda settings: FakeClient())

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

    monkeypatch.setattr(commands, "Settings", FakeSettings)
    monkeypatch.setattr(commands, "ItuHttpClient", lambda settings: FakeClient())

    commands.auth()

    assert "TIES login failed" in capsys.readouterr().out


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

        def download(self, ref, file_format, language, output=None) -> Path:
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

    commands.download("T25-SG12-C-0192", file_format="PDF", language="E")

    assert "7 bytes" in capsys.readouterr().out
