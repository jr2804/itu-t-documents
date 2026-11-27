"""MCP server exposing ITU-T meeting documents.

The server is started with ``itu-t-documents mcp`` and offers tools for the
questions that ITU-T users ask most often: which documents were handled in a
question, who submitted which contribution, and which source is the most
prolific one.

Run it with::

    uv run itu-t-documents mcp
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from itu_t_documents.api import DocumentRecord, ItuDocuments, SourceCount
from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType

#: Instructions shown to the MCP client.
INSTRUCTIONS = """\
Access the documents of ITU-T study group meetings.

Documents are identified by study period, study group, meeting, document type
and number. The metadata of every meeting that was visited is kept in a local
SQLite database, so repeated questions are answered without contacting
www.itu.int again. Downloading a document needs TIES credentials.
"""

#: The MCP server instance.
mcp: FastMCP = FastMCP(
    name="itu-t-documents",
    instructions=INSTRUCTIONS,
)


def _settings() -> Settings:
    """Return the resolved settings."""
    return Settings()


def _period(label: str | None) -> StudyPeriod:
    """Return the study period, defaulting to the current one."""
    if label:
        return StudyPeriod.parse(label)
    return StudyPeriod.current()


def _meeting(code: str) -> MeetingId:
    """Return the meeting identified by a DMS code."""
    return MeetingId.from_code(code)


def _document_payload(record: DocumentRecord) -> dict[str, Any]:
    """Convert a document record into a JSON friendly payload."""
    return {
        "document_id": record.document_id,
        "type": record.doc_type.value,
        "number": record.number,
        "subtype": record.subtype,
        "title": record.title,
        "sources": list(record.sources),
        "questions": list(record.questions),
        "posted": record.posted.isoformat() if record.posted else None,
        "revision": record.revision,
        "study_group": record.study_group,
        "study_period": record.study_period,
        "meeting": record.meeting_code,
        "detail_url": record.detail_url,
    }


def _source_payload(count: SourceCount) -> dict[str, Any]:
    """Convert a source count into a JSON friendly payload."""
    return {
        "source": count.source,
        "documents": count.count,
        "contributions": count.contributions,
        "temporary_documents": count.temporary_documents,
        "meetings": list(count.meetings),
    }


def _sync_meetings(
    api: ItuDocuments,
    study_group: int,
    study_period: StudyPeriod,
    meeting_codes: list[str] | None = None,
) -> list[str]:
    """Make sure the documents of the given meetings are in the local database.

    Args:
        api: The API to use.
        study_group: The study group number.
        study_period: The study period.
        meeting_codes: The DMS codes of the meetings to synchronise. Defaults
            to every meeting of the study group.

    Returns:
        The DMS codes of the synchronised meetings.
    """
    codes = meeting_codes or [meeting.code for meeting in api.list_meetings(study_group, study_period)]
    synced: list[str] = []
    for code in codes:
        try:
            meeting = _meeting(code)
        except ValueError:
            continue
        api.sync_meeting(study_group, meeting, study_period)
        synced.append(code)
    return synced


@mcp.tool
def list_meetings(study_group: int = 12, study_period: str | None = None) -> list[dict[str, Any]]:
    """List the meetings of an ITU-T study group.

    Args:
        study_group: The study group number, e.g. 12.
        study_period: The study period, e.g. "2025-2028". Defaults to the
            current study period.

    Returns:
        The meetings with their DMS code, place and dates.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        return [
            {
                "meeting": meeting.code,
                "place": meeting.place,
                "start_date": meeting.start_date.isoformat(),
                "end_date": meeting.end_date.isoformat() if meeting.end_date else None,
                "label": meeting.label,
            }
            for meeting in api.list_meetings(study_group, period)
        ]
    finally:
        api.close()


@mcp.tool
def list_questions(study_group: int = 12, study_period: str | None = None) -> list[dict[str, Any]]:
    """List the questions under study of an ITU-T study group.

    Args:
        study_group: The study group number, e.g. 12.
        study_period: The study period, e.g. "2025-2028". Defaults to the
            current study period.

    Returns:
        The questions with their working group and rapporteurs.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        return [
            {
                "question": question.code,
                "number": question.number,
                "title": question.title,
                "working_group": question.working_group.code,
                "rapporteurs": [{"name": person.name, "role": person.role.value, "organization": person.organization} for person in question.people],
            }
            for question in api.list_questions(study_group, period)
        ]
    finally:
        api.close()


@mcp.tool
def documents_for_question(
    question: int,
    study_group: int = 12,
    meeting: str | None = None,
    doc_type: str | None = None,
    study_period: str | None = None,
) -> list[dict[str, Any]]:
    """Show the documents handled in a question of an ITU-T study group.

    Use this to answer "show me all TDs of Q5/12 at meeting XYZ": pass the
    question number, the study group and the DMS code of the meeting.

    Args:
        question: The question number, e.g. 5 for Q5/12.
        study_group: The study group number, e.g. 12.
        meeting: The DMS code of the meeting, e.g. "270119". Defaults to every
            meeting of the study group.
        doc_type: Restrict to a document type: "TD", "C", "COL" or "R".
        study_period: The study period, e.g. "2025-2028".

    Returns:
        The matching documents.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        meetings = [meeting] if meeting else None
        _sync_meetings(api, study_group, period, meetings)
        records = api.documents_for_question(
            study_group=study_group,
            question=question,
            meeting=meeting,
            doc_type=DocType(doc_type) if doc_type else None,
        )
        return [_document_payload(record) for record in records]
    finally:
        api.close()


@mcp.tool
def contributions_by_source(source: str, study_group: int = 12, study_period: str | None = None) -> list[dict[str, Any]]:
    """Show the contributions submitted by an organisation.

    Use this to answer "which contributions were made by company XYZ in study
    group 12?".

    Args:
        source: The name of the submitting organisation. The match is case
            insensitive and partial.
        study_group: The study group number, e.g. 12.
        study_period: The study period, e.g. "2025-2028".

    Returns:
        The matching contributions.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        _sync_meetings(api, study_group, period)
        records = api.contributions_by_source(study_group=study_group, source=source)
        return [_document_payload(record) for record in records]
    finally:
        api.close()


@mcp.tool
def top_sources(
    study_group: int = 12,
    last_meetings: int = 3,
    study_period: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Show the sources that submitted the most documents.

    Use this to answer "which source submitted the most documents (TD + C) to
    the last three meetings?".

    Args:
        study_group: The study group number, e.g. 12.
        last_meetings: How many of the most recent meetings to consider.
        study_period: The study period, e.g. "2025-2028".
        limit: The maximum number of sources to report.

    Returns:
        The sources with their document counts, most prolific first.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        meetings = [meeting.code for meeting in api.list_meetings(study_group, period)]
        selected = tuple(meetings[:last_meetings]) if meetings else ()
        _sync_meetings(api, study_group, period, list(selected))
        counts = api.top_sources(study_group=study_group, meetings=selected, limit=limit)
        return [_source_payload(count) for count in counts]
    finally:
        api.close()


@mcp.tool
def search_documents(
    study_group: int = 12,
    *,
    doc_type: str | None = None,
    meeting: str | None = None,
    question: int | None = None,
    source: str | None = None,
    study_period: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search the documents of an ITU-T study group.

    Args:
        study_group: The study group number, e.g. 12.
        doc_type: Restrict to a document type: "TD", "C", "COL" or "R".
        meeting: The DMS code of the meeting, e.g. "270119".
        question: Restrict to a question number.
        source: Restrict to a submitting organisation.
        study_period: The study period, e.g. "2025-2028".
        limit: The maximum number of results.

    Returns:
        The matching documents.
    """
    api = ItuDocuments(_settings())
    try:
        period = _period(study_period)
        _sync_meetings(api, study_group, period, [meeting] if meeting else None)
        records = api.find_documents(
            study_group=study_group,
            doc_type=DocType(doc_type) if doc_type else None,
            meeting=meeting,
            question=question,
            source=source,
            limit=limit,
        )
        return [_document_payload(record) for record in records]
    finally:
        api.close()


@mcp.tool
def download_document(
    document_id: str,
    file_format: str = "PDF",
    language: str = "E",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Download a document from the ITU-T document management system.

    The document has to be available as the requested format and language.
    Downloading needs TIES credentials; a document that was downloaded before is
    served from the local cache.

    Args:
        document_id: The DMS identifier, e.g. "T25-SG12-261015-TD-GEN-0520".
        file_format: "PDF", "MSW" (Word), "ZIP" or "HTM".
        language: The language code: "E", "F", "S", "A", "C" or "R".
        output_path: A path to write the document to. Defaults to the cache.

    Returns:
        The path of the downloaded document and its size in bytes.
    """
    api = ItuDocuments(_settings())
    try:
        ref = DocumentRef.parse(document_id)
        path = api.download(
            ref,
            file_format=DocFormat(file_format.upper()),
            language=DocLanguage(language.upper()),
            output=Path(output_path) if output_path else None,
        )
        return {"path": str(path), "size_bytes": path.stat().st_size}
    finally:
        api.close()


# ----------------------------------------------------------------------
# The catalogue of the ITU-T study groups
# ----------------------------------------------------------------------


@mcp.tool
def list_periods() -> list[dict[str, Any]]:
    """List the study periods of the ITU-T.

    Use this to find the study period a document belongs to. A period is
    named by its years, e.g. "2025-2028", and by its DMS code, e.g. "T25".

    Returns:
        The study periods the ITU-T knows, oldest first.
    """
    current = StudyPeriod.current()
    return [
        {
            "label": period.label,
            "code": period.code,
            "start_year": period.start_year,
            "end_year": period.end_year,
            "current": period == current,
        }
        for period in StudyPeriod.all()
    ]


@mcp.tool
def list_study_groups(study_period: str | None = None) -> list[dict[str, Any]]:
    """List the study groups of a study period.

    The study groups change from period to period, so they are read from the
    ITU-T. Use this before a search to find the study group that holds the
    documents of interest.

    Args:
        study_period: The study period, e.g. "2025-2028" or "2025". Defaults
            to the current study period.

    Returns:
        The study groups of the period, ordered by their number.
    """
    period = _period(study_period)
    api = ItuDocuments(_settings())
    try:
        return [
            {
                "code": group.code,
                "number": group.number,
                "title": group.title,
                "study_period": group.period.label,
            }
            for group in api.catalogue.study_groups(period)
        ]
    finally:
        api.close()


@mcp.tool
def list_structure(study_group: int = 12, study_period: str | None = None) -> dict[str, Any]:
    """Show the structure of an ITU-T study group.

    The structure holds the plenary, the working groups, the questions under
    study and the other groups of the study group — regional groups, focus
    groups and the joint coordination activities.

    Args:
        study_group: The number of the study group, e.g. 12.
        study_period: The study period, e.g. "2025-2028" or "2025". Defaults
            to the current study period.

    Returns:
        The plenary, the working groups, the questions and the other groups.
    """
    period = _period(study_period)
    api = ItuDocuments(_settings())
    try:
        structure = api.catalogue.structure(study_group, period)
    finally:
        api.close()
    return {
        "study_group": structure.study_group.code,
        "study_period": structure.period.label,
        "plenary": structure.plenary.code if structure.plenary else None,
        "working_groups": [{"code": group.code, "name": group.name} for group in structure.working_groups],
        "questions": [
            {"code": question.code, "number": question.number, "title": question.title, "working_group": question.working_group.code}
            for question in structure.questions
        ],
        "other_groups": [{"code": group.code, "title": group.title, "kind": group.kind} for group in structure.other_groups],
    }


@mcp.tool
def search_structure(text: str, study_period: str | None = None) -> list[dict[str, Any]]:
    """Search the working groups, questions and other groups of the ITU-T.

    Use this to find the group that handles a topic, e.g. "speech" or
    "multimedia".

    Args:
        text: The text to look for, e.g. "speech".
        study_period: The study period, e.g. "2025-2028" or "2025". Defaults
            to the current study period.

    Returns:
        The matching entries of the catalogue.
    """
    period = _period(study_period)
    api = ItuDocuments(_settings())
    try:
        entries = api.catalogue.search(text, period)
    finally:
        api.close()
    return [
        {
            "kind": entry.kind,
            "code": entry.code,
            "title": entry.title,
            "study_group": entry.study_group,
            "study_period": entry.period,
        }
        for entry in entries
    ]


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
