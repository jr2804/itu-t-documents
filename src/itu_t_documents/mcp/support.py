"""What the tools share: the package for one tool call, the study period, and the meetings a search synchronises first."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from itu_t_documents.api import ItuDocuments
from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import MeetingId
from itu_t_documents.models.study_periods import StudyPeriod


@contextmanager
def open_api() -> Generator[ItuDocuments]:
    """Open the package for one tool call and close it after the call.

    Yields:
        The API the tool answers from.
    """
    api = ItuDocuments(Settings())
    try:
        yield api
    finally:
        api.close()


def resolve_period(label: str | None) -> StudyPeriod:
    """Return the named study period, or the current one when none is given."""
    if label:
        return StudyPeriod.parse(label)
    return StudyPeriod.current()


def sync_meetings(
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
            meeting = MeetingId.from_code(code)
        except ValueError:
            continue
        api.sync_meeting(study_group, meeting, study_period)
        synced.append(code)
    return synced
