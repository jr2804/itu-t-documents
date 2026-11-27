"""CLI command implementations for ITU-T Document Downloader."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from itu_doc_downloader.api import DocumentRecord, IncompleteListingError, ItuDocuments
from itu_doc_downloader.auth.ties import AuthenticationError
from itu_doc_downloader.cli import args
from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.errors import AccessDeniedError, UnknownEntityError
from itu_doc_downloader.http.client import ItuHttpClient
from itu_doc_downloader.mcp_server import main as run_mcp
from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType
from itu_doc_downloader.urls import period_index


def _period(label: str) -> StudyPeriod:
    """Return the study period named by the user."""
    return StudyPeriod.parse(label)


def _print_documents(records: Sequence[DocumentRecord]) -> None:
    """Print document records as a table."""
    for record in records:
        questions = ",".join(str(number) for number in record.questions) or "-"
        sources = "; ".join(record.sources) or "-"
        print(f"{record.document_id:<32} {record.doc_type.value:<4} Q{questions:<10} {record.title[:60]:<62} {sources[:40]}")


def default() -> None:
    """Show a short introduction to the ITU-T document downloader."""
    print("itu-doc-downloader — access the documents of ITU-T study group meetings.")
    print("Use --help to see the available commands.")


def mcp() -> None:
    """Run the MCP server over stdio."""
    run_mcp()


def auth() -> None:
    """Check whether TIES credentials are configured and usable."""
    settings = Settings()
    if not settings.has_credentials():
        print("No TIES credentials found.")
        print(f"Set ITU_TIES_USERNAME and ITU_TIES_PASSWORD, or store them in {settings.config_file}.")
        return

    with ItuHttpClient(settings) as client:
        try:
            client.authenticate()
        except AuthenticationError as error:
            print(f"TIES login failed: {error}")
            return
    print("TIES login succeeded.")


def meetings(
    study_group: args.StudyGroup = 12,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
) -> None:
    """List the meetings of a study group."""
    with ItuDocuments() as api:
        for meeting in api.list_meetings(study_group, _period(study_period)):
            print(f"{meeting.code}  {meeting.label}")


def questions(
    study_group: args.StudyGroup = 12,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
) -> None:
    """List the questions under study of a study group."""
    with ItuDocuments() as api:
        for question in api.list_questions(study_group, _period(study_period)):
            people = ", ".join(f"{person.name} ({person.role.value})" for person in question.people)
            print(f"{question.code:<8} {question.working_group.code:<10} {question.title}")
            if people:
                print(f"{'':8} {people}")


def sync(
    study_group: args.StudyGroup = 12,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
    meeting: args.Meeting | None = None,
    doc_type: args.DocTypeOption = None,
) -> None:
    """Fetch the documents of a meeting and store them in the local database."""
    types = (DocType(doc_type),) if doc_type else (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT)
    with ItuDocuments() as api:
        period = _period(study_period)
        codes = [meeting] if meeting else [item.code for item in api.list_meetings(study_group, period)]
        total = 0
        for code in codes:
            try:
                stored = api.sync_meeting(study_group, MeetingId.from_code(code), period, types)
            except IncompleteListingError as error:
                print(f"{code}: the listing is incomplete — {error}")
                return
            total += stored
            print(f"{code}: {stored} documents")
        print(f"{total} documents stored in {api.store.database_path}")


def documents(
    study_group: args.StudyGroup = 12,
    *,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
    meeting: args.Meeting | None = None,
    doc_type: args.DocTypeOption = None,
    question: args.Question = None,
    source: args.Source = None,
    limit: args.Limit = None,
) -> None:
    """Search the documents of a study group."""
    with ItuDocuments() as api:
        records = api.find_documents(
            study_group=study_group,
            doc_type=DocType(doc_type) if doc_type else None,
            meeting=meeting,
            question=question,
            source=source,
            limit=limit,
        )
    if not records:
        print("No documents found. Run `itu-doc-downloader sync` first.")
        return
    _print_documents(records)


def download(
    document: args.DocumentId,
    file_format: args.FileFormat = "PDF",
    language: args.Language = "E",
    output_file: args.OutputFile = None,
) -> None:
    """Download a document from the ITU-T document management system."""
    try:
        ref = DocumentRef.parse(document)
    except ValueError:
        print(f"Not a document identifier: {document}")
        return
    with ItuDocuments() as api:
        try:
            path = api.download(
                ref,
                file_format=DocFormat(file_format.upper()),
                language=DocLanguage(language.upper()),
                output=Path(output_file) if output_file else None,
            )
        except FileNotFoundError:
            print(f"{ref.document_id} is not available as {file_format.upper()}-{language.upper()}.")
            print("Run `itu-doc-downloader documents` to see the documents that are known.")
            return
        except AccessDeniedError as error:
            print(f"{error}.")
            print("The membership of a TIES account covers only the study groups it belongs to.")
            return
    print(f"{path} ({path.stat().st_size} bytes)")


# ----------------------------------------------------------------------
# The catalogue of the ITU-T study groups
# ----------------------------------------------------------------------


def periods() -> None:
    """List the study periods the ITU-T knows."""
    for period in StudyPeriod.all():
        marker = " (current)" if period == StudyPeriod.current() else ""
        print(f"{period.label:<12} {period.code:<5} net4 index {period_index(period)}{marker}")


def study_groups(study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD) -> None:
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
    study_group: args.StudyGroup = 12,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
) -> None:
    """Show the structure of a study group."""
    period = _period(study_period)
    with ItuDocuments() as api:
        try:
            found = api.catalogue.structure(study_group, period)
        except UnknownEntityError as error:
            print(f"{error}.")
            return
    if found.plenary is not None:
        print(f"{found.plenary.code:<12} plenary")
    for working_group in found.working_groups:
        print(f"{working_group.code:<12} {working_group.name or ''}")
    for question in found.questions:
        print(f"{question.code:<12} {question.title}")
    for group in found.other_groups:
        print(f"{group.code:<12} {group.title}")


def search(
    text: args.SearchText,
    study_period: args.StudyPeriod = args.DEFAULT_STUDY_PERIOD,
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
