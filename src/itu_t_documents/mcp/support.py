"""What the tools share: the package for one tool call, the study period, and the meetings a search synchronises first."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import httpx

from itu_t_documents.api import ItuDocuments
from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import ItuError
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
    """Make sure the documents a tool needs are in the local database.

    The store is the source of truth: a meeting whose documents are stored is
    not visited again, and a study group with stored documents is answered
    offline. Only a missing study group or a missing meeting contacts the
    ITU-T. A failure to synchronise is reported as an :class:`ItuError`, so
    the tool answers with a message instead of a connection traceback.

    Args:
        api: The API to use.
        study_group: The study group number.
        study_period: The study period.
        meeting_codes: The DMS codes of the meetings to synchronise. Defaults
            to the whole study group when the store holds nothing for it.

    Returns:
        The DMS codes of the synchronised meetings.
    """
    if not meeting_codes:
        if _has_documents(api, study_group, study_period):
            return []
        try:
            api.sync_study_group(study_group, study_period)
        except (ItuError, httpx.HTTPError, OSError) as error:
            raise ItuError(f"could not synchronise study group SG{study_group:02d} for {study_period.label}: {error}") from error
        return []

    synced: list[str] = []
    for code in meeting_codes:
        try:
            meeting = MeetingId.from_code(code)
        except ValueError:
            continue
        if _has_documents(api, study_group, study_period, code):
            continue
        try:
            api.sync_meeting(study_group, meeting, study_period)
        except (ItuError, httpx.HTTPError, OSError) as error:
            raise ItuError(f"could not synchronise meeting {code} of SG{study_group:02d}: {error}") from error
        synced.append(code)
    return synced


def _has_documents(api: ItuDocuments, study_group: int, study_period: StudyPeriod, meeting: str | None = None) -> bool:
    """Whether the store already holds a document of the study group or meeting."""
    return bool(
        api.find_documents(
            study_group=study_group,
            study_period=study_period.label,
            meeting=meeting,
            limit=1,
        )
    )
