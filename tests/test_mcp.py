"""Tests for the MCP server."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from itu_t_documents.catalogue import CatalogueEntry
from itu_t_documents.mcp import mcp, support
from itu_t_documents.models.catalogue import StudyGroup, StudyGroupStructure
from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType
from itu_t_documents.models.questions import Question, WorkingGroup
from itu_t_documents.storage.queries import DocumentRecord, SourceCount


class FakeMeeting:
    """A meeting of the fake API."""

    def __init__(self, code: str, place: str) -> None:
        """Create the fake meeting."""
        self.code = code
        self.place = place
        self.label = f"{place} ({code})"
        self.start_date = date(2027, 1, 19)
        self.end_date = date(2027, 1, 27)


class FakeCatalogue:
    """The catalogue of the fake API."""

    def study_groups(self, period) -> list:
        """Return the study groups of the period."""
        return [StudyGroup(number=12, period=period), StudyGroup(number=21, period=period)]

    def structure(self, study_group: int, period) -> StudyGroupStructure:
        """Return the structure of the study group."""
        group = StudyGroup(number=study_group, period=period)
        return StudyGroupStructure(
            study_group=group,
            plenary=WorkingGroup(code="PLEN", name="PLEN"),
            working_groups=[WorkingGroup(code="WP1/12", name="WP1 12")],
            questions=[
                Question(
                    number=5,
                    study_group=study_group,
                    title="Telephonometric methodologies",
                    working_group=WorkingGroup(code="WP1/12", name="WP1 12"),
                )
            ],
        )

    def search(self, text: str, period=None) -> list:
        """Return the entries that mention the text."""
        return [CatalogueEntry(kind="question", code="Q5/12", title="Telephonometric methodologies", study_group=12, period="2025-2028")]


class FakeApi:
    """A stand-in for the API used by the MCP tools."""

    def __init__(self) -> None:
        """Create the fake API."""
        self.calls: list[tuple] = []
        self.catalogue = FakeCatalogue()
        self.downloaded: Path | None = None

    def download(self, ref: DocumentRef, file_format: DocFormat, language: DocLanguage, output: Path | None = None) -> Path:
        """Return the path of the downloaded document."""
        self.calls.append(("download", ref.document_id, file_format, language, output))
        assert self.downloaded is not None, "the test names the file the download returns"
        return self.downloaded

    def __enter__(self) -> FakeApi:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def close(self) -> None:
        """Close the fake API."""

    def list_meetings(self, study_group: int, study_period) -> list[FakeMeeting]:
        """Return the meetings of the fake study group."""
        self.calls.append(("list_meetings", study_group))
        return [FakeMeeting("270119", "Geneva"), FakeMeeting("261015", "E-Meeting")]

    def list_questions(self, study_group: int, study_period) -> list:
        """Return the questions of the fake study group."""
        self.calls.append(("list_questions", study_group))
        return []

    def sync_meeting(self, study_group: int, meeting, study_period, doc_types=()) -> int:
        """Store the documents of a meeting."""
        self.calls.append(("sync_meeting", study_group, meeting.code, study_period.label))
        return 1

    def documents_for_question(self, **kwargs) -> list[DocumentRecord]:
        """Return the documents of a question."""
        self.calls.append(("documents_for_question", kwargs))
        return [
            DocumentRecord(
                document_id="T25-SG12-261015-TD-GEN-0520",
                doc_type=DocType.TEMPORARY_DOCUMENT,
                number=520,
                subtype="GEN",
                title="Draft agenda for WP1/12",
                sources=("Chair WP1/12",),
                questions=(5,),
                study_group=12,
                study_period="2025-2028",
                meeting_code="261015",
            )
        ]

    def contributions_by_source(self, study_group: int, source: str, study_period: str | None = None) -> list[DocumentRecord]:
        """Return the contributions of a source."""
        self.calls.append(("contributions_by_source", study_group, source, study_period))
        return [
            DocumentRecord(
                document_id="T25-SG12-C-0192",
                doc_type=DocType.CONTRIBUTION,
                number=192,
                subtype=None,
                title="Proposal for a machine-learning speech dataset",
                sources=("Technische Universität Berlin (TU Berlin) (Germany)",),
                questions=(7,),
                study_group=12,
                study_period="2025-2028",
                meeting_code="260609",
            )
        ]

    def top_sources(self, study_group: int, meetings=None, doc_types=(), limit: int = 10) -> list[SourceCount]:
        """Return the most prolific sources."""
        self.calls.append(("top_sources", study_group, meetings))
        return [SourceCount(source="Technische Universität Berlin (TU Berlin) (Germany)", count=3, contributions=3)]

    def find_documents(self, **kwargs) -> list[DocumentRecord]:
        """Return the documents of the fake study group."""
        self.calls.append(("find_documents", kwargs))
        return []


def test_list_meetings_tool(fake_api: FakeApi) -> None:
    """The meetings tool returns the meetings of the study group."""
    result = _call("list_meetings", {"study_group": 12})

    payload = _payload(result)
    assert [item["meeting"] for item in payload] == ["270119", "261015"]
    assert payload[0] == {
        "meeting": "270119",
        "place": "Geneva",
        "start_date": "2027-01-19",
        "end_date": "2027-01-27",
        "label": "Geneva (270119)",
    }
    assert ("list_meetings", 12) in fake_api.calls


def test_list_questions_tool(fake_api: FakeApi) -> None:
    """The questions tool returns the questions of the study group."""
    result = _call("list_questions", {"study_group": 12})

    assert _payload(result) == []
    assert ("list_questions", 12) in fake_api.calls


def test_download_document_tool(fake_api: FakeApi, tmp_path: Path) -> None:
    """The download tool returns the path of the downloaded document."""
    document_file = tmp_path / "document.docx"
    document_file.write_bytes(b"content")
    fake_api.downloaded = document_file

    result = _call("download_document", {"document_id": "T25-SG12-C-0192", "file_format": "msw", "language": "f"})

    payload = _payload(result)
    assert payload == {"path": str(document_file), "size_bytes": 7}
    assert ("download", "T25-SG12-C-0192", DocFormat.WORD, DocLanguage.FRENCH, None) in fake_api.calls


def test_download_document_tool_writes_the_named_file(fake_api: FakeApi, tmp_path: Path) -> None:
    """The download tool passes the output path on."""
    fake_api.downloaded = tmp_path / "document.docx"
    fake_api.downloaded.write_bytes(b"content")

    _call("download_document", {"document_id": "T25-SG12-C-0192", "output_path": "report.docx"})

    call = next(call for call in fake_api.calls if call[0] == "download")
    assert call[4] == Path("report.docx")


def test_documents_for_question_tool(fake_api: FakeApi) -> None:
    """The documents tool answers the question of a meeting."""
    result = _call("documents_for_question", {"question": 5, "study_group": 12, "meeting": "261015"})

    payload = _payload(result)
    assert payload[0]["document_id"] == "T25-SG12-261015-TD-GEN-0520"
    assert payload[0]["type"] == "TD"
    assert payload[0]["questions"] == [5]
    call = next(call for call in fake_api.calls if call[0] == "documents_for_question")
    assert call[1]["question"] == 5
    assert call[1]["meeting"] == "261015"
    assert call[1]["study_period"] is None


def test_documents_for_question_tool_with_a_period(fake_api: FakeApi) -> None:
    """The documents tool names the study period to the stored search."""
    _call("documents_for_question", {"question": 5, "study_group": 12, "study_period": "2022-2024"})

    syncs = [call for call in fake_api.calls if call[0] == "sync_meeting"]
    assert [call[3] for call in syncs] == ["2022-2024", "2022-2024"]
    call = next(call for call in fake_api.calls if call[0] == "documents_for_question")
    assert call[1]["study_period"] == "2022-2024"


def test_contributions_by_source_tool(fake_api: FakeApi) -> None:
    """The contributions tool answers the question of a company."""
    result = _call("contributions_by_source", {"source": "TU Berlin", "study_group": 12})

    payload = _payload(result)
    assert payload[0]["document_id"] == "T25-SG12-C-0192"
    assert payload[0]["type"] == "C"
    assert ("contributions_by_source", 12, "TU Berlin", None) in fake_api.calls


def test_contributions_by_source_tool_with_a_period(fake_api: FakeApi) -> None:
    """The contributions tool names the study period to the stored search."""
    _call("contributions_by_source", {"source": "TU Berlin", "study_group": 12, "study_period": "2022-2024"})

    assert ("contributions_by_source", 12, "TU Berlin", "2022-2024") in fake_api.calls


def test_top_sources_tool(fake_api: FakeApi) -> None:
    """The top sources tool answers the question of the most prolific sources."""
    result = _call("top_sources", {"study_group": 12, "last_meetings": 3})

    payload = _payload(result)
    assert payload[0]["source"] == "Technische Universität Berlin (TU Berlin) (Germany)"
    assert payload[0]["documents"] == 3
    call = next(call for call in fake_api.calls if call[0] == "top_sources")
    assert call[2] == ("270119", "261015")


def test_search_documents_tool(fake_api: FakeApi) -> None:
    """The search tool passes the filters on."""
    result = _call("search_documents", {"study_group": 12, "doc_type": "TD"})

    assert _payload(result) == []
    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["doc_type"] is DocType.TEMPORARY_DOCUMENT
    assert call[1]["study_period"] is None


def test_search_documents_tool_with_a_period(fake_api: FakeApi) -> None:
    """The search tool passes the named study period to the stored search."""
    _call("search_documents", {"study_group": 12, "study_period": "2017-2020"})

    call = next(call for call in fake_api.calls if call[0] == "find_documents")
    assert call[1]["study_period"] == "2017-2020"


def test_list_periods_tool() -> None:
    """The periods tool returns the study periods of the ITU-T."""
    result = _call("list_periods", {})

    payload = _payload(result)
    assert any(item["label"] == "2025-2028" for item in payload)
    assert any(item["current"] for item in payload)


def test_list_study_groups_tool(fake_api: FakeApi) -> None:
    """The study groups tool returns the study groups of a period."""
    result = _call("list_study_groups", {"study_period": "2025-2028"})

    payload = _payload(result)
    assert [item["code"] for item in payload] == ["SG12", "SG21"]


def test_list_structure_tool(fake_api: FakeApi) -> None:
    """The structure tool returns the groups of a study group."""
    result = _call("list_structure", {"study_group": 12, "study_period": "2025-2028"})

    payload = _payload(result)
    assert payload["study_group"] == "SG12"
    assert payload["plenary"] == "PLEN"
    assert payload["working_groups"][0]["code"] == "WP1/12"
    assert payload["questions"][0]["code"] == "Q5/12"


def test_search_structure_tool(fake_api: FakeApi) -> None:
    """The catalogue search tool returns the matching entries."""
    result = _call("search_structure", {"text": "speech", "study_period": "2025-2028"})

    payload = _payload(result)
    assert payload[0]["code"] == "Q5/12"
    assert payload[0]["kind"] == "question"


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    """Replace the API used by the MCP tools."""
    api = FakeApi()
    monkeypatch.setattr(support, "ItuDocuments", lambda *args, **kwargs: api)
    return api


def _call(name: str, arguments: dict) -> object:
    """Call an MCP tool and return its result."""
    return asyncio.run(mcp.call_tool(name, arguments))


def _payload(result) -> Any:
    """Return the decoded payload of a tool result."""
    if result.content:
        return json.loads(result.content[0].text)
    return result.structured_content["result"]
