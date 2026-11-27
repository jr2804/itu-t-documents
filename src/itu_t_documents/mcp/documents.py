"""The tools that search the documents of a study group."""

from __future__ import annotations

from typing import Any

from itu_t_documents.mcp.payloads import document_payload
from itu_t_documents.mcp.support import open_api, resolve_period, sync_meetings
from itu_t_documents.models.enums import DocType


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
        study_period: Restrict to a study period, e.g. "2022-2024". Defaults
            to every study period that is stored.

    Returns:
        The matching documents.
    """
    period = resolve_period(study_period)
    with open_api() as api:
        sync_meetings(api, study_group, period, [meeting] if meeting else None)
        records = api.documents_for_question(
            study_group=study_group,
            question=question,
            meeting=meeting,
            doc_type=DocType(doc_type) if doc_type else None,
            study_period=period.label if study_period else None,
        )
        return [document_payload(record) for record in records]


def contributions_by_source(source: str, study_group: int = 12, study_period: str | None = None) -> list[dict[str, Any]]:
    """Show the contributions submitted by an organisation.

    Use this to answer "which contributions were made by company XYZ in study
    group 12?".

    Args:
        source: The name of the submitting organisation. The match is case
            insensitive and partial.
        study_group: The study group number, e.g. 12.
        study_period: Restrict to a study period, e.g. "2022-2024". Defaults
            to every study period that is stored.

    Returns:
        The matching contributions.
    """
    period = resolve_period(study_period)
    with open_api() as api:
        sync_meetings(api, study_group, period)
        records = api.contributions_by_source(study_group=study_group, source=source, study_period=period.label if study_period else None)
        return [document_payload(record) for record in records]


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
        study_period: Restrict to a study period, e.g. "2022-2024". Defaults
            to every study period that is stored.
        limit: The maximum number of results.

    Returns:
        The matching documents.
    """
    period = resolve_period(study_period)
    with open_api() as api:
        sync_meetings(api, study_group, period, [meeting] if meeting else None)
        records = api.find_documents(
            study_group=study_group,
            study_period=period.label if study_period else None,
            doc_type=DocType(doc_type) if doc_type else None,
            meeting=meeting,
            question=question,
            source=source,
            limit=limit,
        )
        return [document_payload(record) for record in records]
