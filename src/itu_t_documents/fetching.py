"""Read the ITU-T web site.

The functions take the HTTP client to read with and return what a page of
the ITU-T Document Management System tells: the meetings of a study group,
the questions under study, the listings of documents and the detail page of
a document. Nothing is stored here; :class:`itu_t_documents.ItuDocuments`
stores what these functions read.
"""

from __future__ import annotations

from urllib.parse import urljoin

from itu_t_documents.errors import IncompleteListingError
from itu_t_documents.http.client import ItuClient
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.questions import Question
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.scraping import detail as detail_scraper
from itu_t_documents.scraping import listing as listing_scraper
from itu_t_documents.scraping import meetings as meetings_scraper
from itu_t_documents.scraping import questions as questions_scraper
from itu_t_documents.urls import detail_url, listing_url, meeting_index_url, period_index, questions_url


def list_meetings(client: ItuClient, study_group: int, study_period: StudyPeriod) -> list[meetings_scraper.MeetingInfo]:
    """List the meetings of a study group.

    Args:
        client: The HTTP client to read the pages with.
        study_group: The study group number.
        study_period: The study period.

    Returns:
        The meetings found, in the order of the ITU-T pages.
    """
    url = meeting_index_url(study_period, study_group)
    page = client.get_text(url)
    return meetings_scraper.parse_meeting_index(page)


def list_questions(client: ItuClient, study_group: int, study_period: StudyPeriod) -> list[Question]:
    """List the questions under study of a study group.

    Args:
        client: The HTTP client to read the pages with.
        study_group: The study group number.
        study_period: The study period.

    Returns:
        The questions found, ordered by question number.
    """
    index = period_index(study_period)
    page = client.get_text(questions_url(study_group, index))
    return questions_scraper.parse_questions(page, study_group)


def fetch_documents(
    client: ItuClient,
    study_group: int,
    doc_type: DocType,
    study_period: StudyPeriod,
    meeting: MeetingId | None = None,
) -> list[DocumentMetadata]:
    """Fetch a document listing from the ITU-T web site.

    Every page of the listing is read. The aggregate listing of the
    temporary documents of a meeting only shows a preview of five documents
    per sub-type, so the listing of every sub-type is fetched as well.

    Args:
        client: The HTTP client to read the pages with.
        study_group: The study group number.
        doc_type: The document type to list.
        study_period: The study period.
        meeting: The meeting to list the documents of.

    Returns:
        The metadata of the listed documents.

    Raises:
        IncompleteListingError: When a listing reports more documents than
            were read from its pages.
    """
    page, documents = _read_listing(client, study_period, study_group, doc_type, meeting=meeting)
    if doc_type is not DocType.TEMPORARY_DOCUMENT or meeting is None:
        _check_complete(page, documents)
        return documents

    subtypes = listing_scraper.parse_subtypes(page, meeting)
    if not subtypes:
        _check_complete(page, documents)
        return documents

    seen = {document.ref.document_id for document in documents}
    for subtype in subtypes:
        subtype_page, subtype_documents = _read_listing(client, study_period, study_group, doc_type, meeting=meeting, subtype=subtype)
        _check_complete(subtype_page, subtype_documents)
        for document in subtype_documents:
            if document.ref.document_id in seen:
                continue
            seen.add(document.ref.document_id)
            documents.append(document)
    return documents


def fetch_document_detail(client: ItuClient, ref: DocumentRef) -> DocumentMetadata:
    """Fetch the detail page of a document.

    Args:
        client: The HTTP client to read the page with.
        ref: The identity of the document.

    Returns:
        The metadata of the document, including its available renditions.
    """
    page = client.get_text(detail_url(ref.document_id))
    return DocumentMetadata(
        ref=ref,
        title=detail_scraper.parse_title(page),
        files=detail_scraper.parse_files(page),
        detail_url=detail_url(ref.document_id),
    )


def _read_listing(
    client: ItuClient,
    study_period: StudyPeriod,
    study_group: int,
    doc_type: DocType,
    *,
    meeting: MeetingId | None = None,
    subtype: str | None = None,
) -> tuple[str, list[DocumentMetadata]]:
    """Read every page of a listing.

    A listing longer than the page size spans several pages, which are
    read one after the other until the last page. A page that was read
    already, or that holds no document that was not read, ends the
    reading, so a defective link cannot loop forever; the completeness
    check then reports the missing documents.

    Args:
        client: The HTTP client to read the pages with.
        study_period: The study period.
        study_group: The study group number.
        doc_type: The document type to list.
        meeting: The meeting to list the documents of.
        subtype: The sub-type of the temporary documents to list.

    Returns:
        The first page of the listing and the metadata of the documents
        read from every page, each document once.
    """
    url = listing_url(study_period, study_group, doc_type, meeting, subtype)
    first_page = page = client.get_text(url)
    documents = listing_scraper.parse_listing(page, study_period, study_group, doc_type, meeting)
    read = {document.ref.document_id for document in documents}
    visited = {url}
    while (next_page := listing_scraper.parse_next_page(page)) is not None:
        page_url = urljoin(url, next_page)
        if page_url in visited:
            break
        visited.add(page_url)
        page = client.get_text(page_url)
        further_documents = [
            document for document in listing_scraper.parse_listing(page, study_period, study_group, doc_type, meeting) if document.ref.document_id not in read
        ]
        if not further_documents:
            break
        read.update(document.ref.document_id for document in further_documents)
        documents.extend(further_documents)
    return first_page, documents


def _check_complete(page: str, documents: list[DocumentMetadata]) -> None:
    """Raise when a listing holds fewer documents than it reports.

    Args:
        page: The HTML of the first page of the listing.
        documents: The documents that were parsed from every page of the
            listing.

    Raises:
        IncompleteListingError: When the listing reports more documents than
            were parsed from it.
    """
    reported = listing_scraper.parse_total_items(page)
    if reported is not None and reported > len(documents):
        raise IncompleteListingError(f"the listing holds {len(documents)} of {reported} documents; not every page of the ITU-T listing could be read")
