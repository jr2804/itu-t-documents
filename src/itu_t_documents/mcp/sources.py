"""The tool that counts the documents of the most prolific sources."""

from __future__ import annotations

from itu_t_documents.mcp.payloads import SourcePayload, source_payload
from itu_t_documents.mcp.support import open_api, resolve_period, sync_meetings
from itu_t_documents.urls import DEFAULT_STUDY_GROUP


def top_sources(
    study_group: int = DEFAULT_STUDY_GROUP,
    last_meetings: int = 3,
    study_period: str | None = None,
    limit: int = 10,
) -> list[SourcePayload]:
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
    period = resolve_period(study_period)
    with open_api() as api:
        sync_meetings(api, study_group, period)
        counts = api.top_sources(
            study_group=study_group,
            last_meetings=last_meetings,
            study_period=period,
            limit=limit,
        )
        return [source_payload(count) for count in counts]
