"""CLI command implementations for ITU-T Documents."""

from __future__ import annotations

from pathlib import Path

from itu_t_documents.api import ItuDocuments
from itu_t_documents.cli import args
from itu_t_documents.cli.formatting import print_documents
from itu_t_documents.cli.startup import auth, default, mcp
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.urls import DEFAULT_STUDY_GROUP, period_index

__all__ = ["auth", "default", "mcp"]


def meetings(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    study_period: args.StudyPeriod = None,
) -> None:
    """List the meetings of a study group."""
    with ItuDocuments() as api:
        for meeting in api.list_meetings(study_group, _period(study_period)):
            print(f"{meeting.code}  {meeting.label}")


def sync(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    study_period: args.StudyPeriod = None,
    meeting: args.Meeting | None = None,
    doc_type: args.DocTypeOption = None,
) -> None:
    """Fetch the documents of a meeting and store them in the local database."""
    types = (doc_type,) if doc_type else (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT)
    with ItuDocuments() as api:
        period = _period(study_period)
        if meeting:
            stored = api.sync_meeting(study_group, MeetingId.from_code(meeting), period, types)
            print(f"{meeting}: {stored} documents")
            total = stored
        else:
            report = api.sync_study_group(study_group, period, types)
            for code, stored in report.meetings:
                print(f"{code}: {stored} documents")
            if report.period_only:
                print(f"the period listing: {report.period_only} documents")
            total = report.total
        print(f"{total} documents stored in {api.store.database_path}")


def documents(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    *,
    study_period: args.StudyPeriodFilter = None,
    meeting: args.Meeting | None = None,
    doc_type: args.DocTypeOption = None,
    question: args.Question = None,
    source: args.Source = None,
    limit: args.Limit = None,
) -> None:
    """Search the documents of a study group."""
    period = _period(study_period) if study_period else None
    with ItuDocuments() as api:
        records = api.find_documents(
            study_group=study_group,
            study_period=period.label if period is not None else None,
            doc_type=doc_type,
            meeting=meeting,
            question=question,
            source=source,
            limit=limit,
        )
    if not records:
        print("No documents found. Run `itu-t-documents sync` first.")
        return
    print_documents(records)


def download(
    document: args.DocumentId,
    file_format: args.FileFormat = DocFormat.PDF,
    language: args.Language = DocLanguage.ENGLISH,
    output_file: args.OutputFile = None,
) -> None:
    """Download a document from the ITU-T document management system."""
    ref = DocumentRef.parse(document)
    with ItuDocuments() as api:
        path_file = api.download(
            ref,
            file_format=file_format,
            language=language,
            output_file=Path(output_file) if output_file else None,
        )
    print(f"{path_file} ({path_file.stat().st_size} bytes)")


def periods() -> None:
    """List the study periods the ITU-T knows."""
    for period in StudyPeriod.all():
        marker = " (current)" if period == StudyPeriod.current() else ""
        print(f"{period.label:<12} {period.code:<5} net4 index {period_index(period)}{marker}")


def study_groups(study_period: args.StudyPeriod = None) -> None:
    """List the study groups of a study period."""
    period = _period(study_period)
    with ItuDocuments() as api:
        groups = api.catalogue.study_groups(period)
    if not groups:
        print(f"The ITU-T publishes no study group for {period.label}.")
        return
    for group in groups:
        print(f"{group.code:<6} {group.label}")


def structure(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    study_period: args.StudyPeriod = None,
) -> None:
    """Show the structure of a study group."""
    period = _period(study_period)
    with ItuDocuments() as api:
        found = api.catalogue.structure(study_group, period)
    if found.plenary is not None:
        print(f"{found.plenary.code:<12} plenary")
    for working_group in found.working_groups:
        print(f"{working_group.code:<12} {working_group.name or ''}")
    for question in found.questions:
        print(f"{question.code:<12} {question.title}")
    for group in found.other_groups:
        print(f"{group.code:<12} {group.title}")


def questions(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    study_period: args.StudyPeriod = None,
) -> None:
    """List the questions under study of a study group."""
    with ItuDocuments() as api:
        for question in api.list_questions(study_group, _period(study_period)):
            people = ", ".join(f"{person.name} ({person.role.value})" for person in question.people)
            print(f"{question.code:<8} {question.working_group.code:<10} {question.title}")
            if people:
                print(f"{'':8} {people}")


def search(
    text: args.SearchText,
    study_period: args.StudyPeriod = None,
) -> None:
    """Search the working groups, questions and other groups of the ITU-T."""
    period = _period(study_period)
    with ItuDocuments() as api:
        entries = api.catalogue.search(text, period)
    if not entries:
        print(f"Nothing in {period.label} matches {text!r}.")
        return
    for entry in entries:
        print(f"{entry.kind:<16} {entry.code:<14} {entry.title}")


def top_sources(
    study_group: args.StudyGroup = DEFAULT_STUDY_GROUP,
    last_meetings: args.LastMeetings = 3,
    study_period: args.StudyPeriod = None,
    limit: args.Limit = 10,
) -> None:
    """Show the sources that submitted the most documents."""
    period = _period(study_period)
    with ItuDocuments() as api:
        counts = api.top_sources(
            study_group=study_group,
            last_meetings=last_meetings,
            study_period=period,
            limit=limit or 10,
        )
    if not counts:
        print("No documents found. Run `itu-t-documents sync` first.")
        return
    for count in counts:
        print(f"{count.count:>6}  {count.source}")


def _period(label: str | None) -> StudyPeriod:
    """Return the named study period, or the current one when none is given.

    An option that is empty, as an environment variable that is set to an
    empty string leaves it, counts as not given.
    """
    return StudyPeriod.parse(label) if label else StudyPeriod.current()
