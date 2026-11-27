"""The tools that list the meetings and the questions of a study group."""

from __future__ import annotations

from itu_t_documents.mcp.payloads import MeetingPayload, QuestionPayload, person_payload
from itu_t_documents.mcp.support import open_api, resolve_period
from itu_t_documents.models.enums import Role
from itu_t_documents.urls import DEFAULT_STUDY_GROUP


def list_meetings(study_group: int = DEFAULT_STUDY_GROUP, study_period: str | None = None) -> list[MeetingPayload]:
    """List the meetings of an ITU-T study group.

    Args:
        study_group: The study group number, e.g. 12.
        study_period: The study period, e.g. "2025-2028". Defaults to the
            current study period.

    Returns:
        The meetings with their DMS code, place and dates.
    """
    period = resolve_period(study_period)
    with open_api() as api:
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


def list_questions(study_group: int = DEFAULT_STUDY_GROUP, study_period: str | None = None) -> list[QuestionPayload]:
    """List the questions under study of an ITU-T study group.

    Args:
        study_group: The study group number, e.g. 12.
        study_period: The study period, e.g. "2025-2028". Defaults to the
            current study period.

    Returns:
        The questions with their working group and the people who hold a role.
    """
    period = resolve_period(study_period)
    with open_api() as api:
        return [
            {
                "question": question.code,
                "number": question.number,
                "title": question.title,
                "working_group": question.working_group.code,
                "rapporteurs": [person_payload(person) for person in question.rapporteurs],
                "co_rapporteurs": [person_payload(person) for person in question.co_rapporteurs],
                "other_people": [person_payload(person) for person in question.people if person.role not in (Role.RAPPORTEUR, Role.CO_RAPPORTEUR)],
            }
            for question in api.list_questions(study_group, period)
        ]
