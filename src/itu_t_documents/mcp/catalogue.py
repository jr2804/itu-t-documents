"""The tools that answer questions about the catalogue of the ITU-T."""

from __future__ import annotations

from typing import Any

from itu_t_documents.mcp.support import open_api, resolve_period
from itu_t_documents.models.study_periods import StudyPeriod


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
    period = resolve_period(study_period)
    with open_api() as api:
        return [
            {
                "code": group.code,
                "number": group.number,
                "title": group.title,
                "study_period": group.period.label,
            }
            for group in api.catalogue.study_groups(period)
        ]


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
    period = resolve_period(study_period)
    with open_api() as api:
        structure = api.catalogue.structure(study_group, period)
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
    period = resolve_period(study_period)
    with open_api() as api:
        entries = api.catalogue.search(text, period)
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
