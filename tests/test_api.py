"""Tests for the high level API."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from sqlmodel import select

from itu_t_documents import fetching
from itu_t_documents.api import ItuDocuments
from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import AccessDeniedError, AuthenticationError, IncompleteListingError, InvalidDocumentError, ScrapingError
from itu_t_documents.models.documents import DocumentRef, MeetingId
from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.study_periods import StudyPeriod
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.tables import DocumentRow
from tests.fakes import DOCUMENT_BYTES, POLICY_PAGE, FakeClient

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def test_list_meetings(api: ItuDocuments) -> None:
    """The API lists the meetings of a study group."""
    found = api.list_meetings(12, StudyPeriod(start_year=2025, end_year=2028))

    assert [meeting.code for meeting in found][:3] == ["270119", "261015", "260609"]


def test_list_questions(api: ItuDocuments) -> None:
    """The API lists the questions under study of a study group."""
    found = api.list_questions(12, StudyPeriod(start_year=2025, end_year=2028))

    assert [question.code for question in found][:3] == ["Q1/12", "Q2/12", "Q4/12"]
    assert found[0].working_group.code == "PLEN"


def test_sync_meeting_stores_the_documents(api: ItuDocuments) -> None:
    """Syncing a meeting stores the documents of the meeting."""
    stored = api.sync_meeting(
        12,
        MeetingId.from_code("260609"),
        StudyPeriod(start_year=2025, end_year=2028),
        (DocType.CONTRIBUTION,),
    )

    assert stored == 3
    assert api.store.count_documents() == 3


def test_fetch_documents_reads_every_subtype(api: ItuDocuments, fake_client: FakeClient) -> None:
    """The temporary documents of a meeting are read per sub-type."""
    documents = api.fetch_documents(
        12,
        DocType.TEMPORARY_DOCUMENT,
        StudyPeriod(start_year=2025, end_year=2028),
        MeetingId.from_code("261015"),
    )

    assert documents
    assert "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN" in fake_client.requested
    assert "T25-SG12-261015-TD-GEN-0523" in {document.document_id for document in documents}


def test_fetch_documents_without_a_subtype(api: ItuDocuments, fake_client: FakeClient) -> None:
    """A listing that offers no sub-type is read as it is."""
    documents = api.fetch_documents(
        12,
        DocType.TEMPORARY_DOCUMENT,
        StudyPeriod(start_year=2025, end_year=2028),
        MeetingId.from_code("250114"),
    )

    assert documents
    assert not any(url.endswith("-TD-GEN") for url in fake_client.requested)


def test_fetch_documents_of_a_truncated_listing(api: ItuDocuments) -> None:
    """A listing that holds fewer documents than it reports is refused."""
    with pytest.raises(IncompleteListingError):
        api.fetch_documents(
            12,
            DocType.CONTRIBUTION,
            StudyPeriod(start_year=2025, end_year=2028),
            MeetingId.from_code("270119"),
        )


def test_fetch_documents_reads_every_page(api: ItuDocuments, fake_client: FakeClient) -> None:
    """A listing that spans several pages is read to its last page."""
    documents = api.fetch_documents(12, DocType.REPORT, StudyPeriod(start_year=2025, end_year=2028))

    assert [document.ref.document_id for document in documents] == [f"T25-SG12-R-{number:04d}" for number in range(14, 0, -1)]
    listing_requests = [url for url in fake_client.requested if "parent=T25-SG12-R" in url]
    assert listing_requests == [
        "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-R",
        "https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T25-SG12-R&PageLB=10",
    ]


def test_fetch_documents_of_a_listing_with_an_unreadable_page(api: ItuDocuments, fake_client: FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A listing whose next page cannot be read is refused, not stored in part."""
    read_page = fake_client.get_text
    monkeypatch.setattr(fake_client, "get_text", lambda url: "" if url.endswith("&PageLB=10") else read_page(url))

    with pytest.raises(ScrapingError, match="cannot read document listing"):
        api.fetch_documents(12, DocType.REPORT, StudyPeriod(start_year=2025, end_year=2028))


def test_find_documents_by_question(api: ItuDocuments) -> None:
    """The stored documents can be searched by question."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    records = api.documents_for_question(study_group=12, question=7)

    assert len(records) == 1
    assert records[0].document_id == "T25-SG12-C-0192"
    assert records[0].sources == ("Technische Universität Berlin (TU Berlin) (Germany)",)
    assert records[0].meeting_code == "260609"


def test_find_documents_by_source(api: ItuDocuments) -> None:
    """The stored documents can be searched by source."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    records = api.contributions_by_source(study_group=12, source="Hottinger")

    assert len(records) == 1
    assert records[0].number == 191
    assert records[0].sources == ("Hottinger Brüel & Kjaer A/S (Denmark)",)


def test_find_documents_returns_each_document_once_for_a_source(api: ItuDocuments) -> None:
    """A document that several matching sources submitted is returned once."""
    for number, sources in ((1, ["Acme Corp", "Acme Europe"]), (2, ["Acme Asia"])):
        ref = DocumentRef(study_period=PERIOD, study_group=12, doc_type=DocType.CONTRIBUTION, number=number)
        api.store.store_document(DocumentMetadata(ref=ref, title=f"Document {number}", sources=sources))

    records = api.find_documents(study_group=12, source="Acme")

    assert [record.number for record in records] == [2, 1]
    assert len(api.find_documents(study_group=12, source="Acme", limit=1)) == 1


def test_documents_for_question_of_one_study_period(api: ItuDocuments) -> None:
    """The study period tells which stored documents of a question are listed."""
    old_period = StudyPeriod(start_year=2022, end_year=2024)
    for period, meeting in ((PERIOD, "260609"), (old_period, "221121")):
        ref = DocumentRef(study_period=period, study_group=12, doc_type=DocType.CONTRIBUTION, number=192, meeting=MeetingId.from_code(meeting))
        api.store.store_document(DocumentMetadata(ref=ref, title="Proposal", sources=["TU Berlin"], questions=[7]))

    every = api.documents_for_question(study_group=12, question=7)
    assert {record.document_id for record in every} == {"T25-SG12-C-0192", "T22-SG12-C-0192"}

    old = api.documents_for_question(study_group=12, question=7, study_period=old_period.label)
    assert [record.document_id for record in old] == ["T22-SG12-C-0192"]
    assert [record.document_id for record in api.contributions_by_source(study_group=12, source="TU Berlin", study_period=old_period.label)] == [
        "T22-SG12-C-0192"
    ]


def test_the_detail_page_keeps_what_the_listing_told(api: ItuDocuments) -> None:
    """Reading the detail page of a stored document does not erase its listing."""
    api.sync_meeting(12, MeetingId.from_code("260609"), PERIOD, (DocType.CONTRIBUTION,))
    listed = {record.document_id: record for record in api.find_documents(study_group=12)}

    api.sync_detail(DocumentRef.parse("T25-SG12-C-0191"))
    api.download(DocumentRef.parse("T25-SG12-C-0192"), DocFormat.WORD, DocLanguage.ENGLISH)

    kept = {record.document_id: record for record in api.find_documents(study_group=12)}
    assert set(kept) == set(listed)
    for document_id, record in kept.items():
        assert record.posted == listed[document_id].posted, document_id
        assert record.posted is not None
        assert record.meeting_code == listed[document_id].meeting_code == "260609"
        assert record.sources == listed[document_id].sources


def test_top_sources(api: ItuDocuments) -> None:
    """The sources are counted by the number of submitted documents."""
    api.sync_meeting(12, MeetingId.from_code("260609"), StudyPeriod(start_year=2025, end_year=2028), (DocType.CONTRIBUTION,))

    counts = api.top_sources(study_group=12, meetings=("260609",))

    assert counts
    assert {count.source for count in counts} == {
        "Technische Universität Berlin (TU Berlin) (Germany)",
        "Hottinger Brüel & Kjaer A/S (Denmark)",
        "Zambia Information & Communications Technology Authority (ZICTA) (Zambia)",
    }
    assert all(count.contributions == 1 for count in counts)
    assert all(count.temporary_documents == 0 for count in counts)
    assert all(count.meetings == ("260609",) for count in counts)


def test_sync_period_stores_contributions_without_a_meeting(api: ItuDocuments) -> None:
    """The period-wide listing stores a contribution that no meeting listing names."""
    stored = api.sync_period(12, PERIOD, (DocType.CONTRIBUTION,))

    assert stored > 0
    assert api.find_documents(study_group=12, doc_type=DocType.CONTRIBUTION)


def test_sync_period_skips_the_previewed_temporary_documents(api: ItuDocuments) -> None:
    """Temporary documents are read meeting by meeting, not from the aggregate listing."""
    stored = api.sync_period(12, PERIOD, (DocType.TEMPORARY_DOCUMENT, DocType.CONTRIBUTION))

    assert stored > 0
    assert not api.find_documents(study_group=12, doc_type=DocType.TEMPORARY_DOCUMENT)


def test_sync_study_group_reports_what_every_meeting_stored(api: ItuDocuments, monkeypatch: pytest.MonkeyPatch) -> None:
    """A study-group synchronisation reports the documents stored per meeting."""
    monkeypatch.setattr(api, "list_meetings", lambda *args: [SimpleNamespace(code="260609"), SimpleNamespace(code="250909")])
    monkeypatch.setattr(api, "sync_meeting", lambda *args: 2)
    monkeypatch.setattr(api, "sync_period", lambda *args: 1)

    report = api.sync_study_group(12, PERIOD, (DocType.CONTRIBUTION,))

    assert report.meetings == (("260609", 2), ("250909", 2))
    assert report.period_only == 1
    assert report.total == 5


def test_top_sources_uses_the_most_recent_stored_meetings(api: ItuDocuments) -> None:
    """The last-meetings filter selects the newest meeting codes in the store."""
    for number, meeting in ((1, "250909"), (2, "260609")):
        ref = DocumentRef(study_period=PERIOD, study_group=12, doc_type=DocType.CONTRIBUTION, number=number, meeting=MeetingId.from_code(meeting))
        api.store.store_document(DocumentMetadata(ref=ref, title=f"Document {number}", sources=["Acme"]))

    counts = api.top_sources(study_group=12, last_meetings=1)

    assert counts
    assert all(count.meetings == ("260609",) for count in counts)


def test_a_listing_page_without_new_documents_ends_the_reading(api: ItuDocuments, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A next page that repeats the documents already read ends the reading."""
    page = (fixtures_dir / "listing_contributions.html").read_text(encoding="utf-8")

    class SamePageClient:
        def get_text(self, url: str) -> str:
            return page

        def authenticate(self, target: str | None = None) -> httpx.Client:
            return cast(httpx.Client, self)

        def close(self) -> None:
            return None

    monkeypatch.setattr(fetching.listing_scraper, "parse_next_page", lambda page: "/md/next")

    first, documents = fetching._read_listing(SamePageClient(), PERIOD, 12, DocType.CONTRIBUTION)

    assert first == page
    assert documents


def test_download_a_revised_document(api: ItuDocuments) -> None:
    """The original of a revised document is downloaded."""
    ref = DocumentRef.parse("T25-SG02-C-0001")

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.name == "MSW-E.docx"
    assert path.read_bytes() == DOCUMENT_BYTES


def test_download_writes_the_fresh_rendition_to_an_output_file(api: ItuDocuments, tmp_path: Path) -> None:
    """A downloaded rendition is copied to the requested output file."""
    output = tmp_path / "out" / "contribution.docx"

    path = api.download(DocumentRef.parse("T25-SG12-C-0192"), DocFormat.WORD, DocLanguage.ENGLISH, output_file=output)

    assert path == output
    assert output.read_bytes() == DOCUMENT_BYTES


def test_download_writes_a_cached_rendition_to_an_output_file(api: ItuDocuments, tmp_path: Path) -> None:
    """A cached rendition is copied to the requested output file without a request."""
    ref = DocumentRef.parse("T25-SG12-C-0192")
    api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    output = tmp_path / "out" / "contribution.docx"

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH, output_file=output)

    assert path == output
    assert output.read_bytes() == DOCUMENT_BYTES


def test_download_a_document_that_was_only_revised(api: ItuDocuments) -> None:
    """A revision is downloaded when the original is gone."""
    ref = DocumentRef.parse("T25-SG02-C-0002")

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.name == "MSW-E-R1.docx"
    assert path.read_bytes() == DOCUMENT_BYTES


def test_a_collective_letter_still_authenticates(api: ItuDocuments, fake_client: FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A public collective letter goes through the authenticated download path."""

    def refuse(target: str | None = None) -> httpx.Client:
        """Refuse the login the download asks for."""
        raise AuthenticationError("no TIES credentials configured")

    monkeypatch.setattr(fake_client, "authenticate", refuse)

    with pytest.raises(AuthenticationError, match="no TIES credentials"):
        api.download(DocumentRef.parse("T25-SG12-COL-0006"), DocFormat.WORD, DocLanguage.ENGLISH)


def test_download_a_document_the_account_may_not_see(api: ItuDocuments, fake_client: FakeClient) -> None:
    """A document outside the membership of the account is refused."""
    fake_client.denied = True

    with pytest.raises(AccessDeniedError, match="SG13"):
        api.download(DocumentRef.parse("T25-SG13-C-0001"), DocFormat.WORD, DocLanguage.ENGLISH)


def test_download_a_document_that_is_gone(api: ItuDocuments, fake_client: FakeClient) -> None:
    """A document that the ITU-T does not have any more is reported."""
    fake_client.missing = True

    with pytest.raises(FileNotFoundError):
        api.download(DocumentRef.parse("T25-SG12-C-0192"), DocFormat.WORD, DocLanguage.ENGLISH)


def test_download_refuses_the_page_of_the_access_policy(api: ItuDocuments, fake_client: FakeClient) -> None:
    """The page of the access policy is not a document and is not stored as one."""
    fake_client.policy_page = True

    with pytest.raises(InvalidDocumentError, match="was not downloaded"):
        api.download(DocumentRef.parse("T25-SG12-C-0192"), DocFormat.WORD, DocLanguage.ENGLISH)

    assert not (api.cache.root_dir / "T25-SG12-C-0192").exists()


def test_a_cached_page_of_the_access_policy_is_downloaded_again(api: ItuDocuments) -> None:
    """A file that an older release cached from the access policy is not handed out."""
    ref = DocumentRef.parse("T25-SG12-C-0192")
    cached = api.cache.path_for(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(POLICY_PAGE)

    downloaded = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)

    assert downloaded.read_bytes() == DOCUMENT_BYTES


def test_fetch_documents_of_a_listing_whose_next_link_loops(
    api: ItuDocuments, fake_client: FakeClient, monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path
) -> None:
    """A next link that leads back to a page that was read ends the reading."""
    last_page = (fixtures_dir / "listing_reports_last_page.html").read_text(encoding="utf-8")
    current = '<font color="red"><strong>2</strong></font>'
    looping = last_page.replace(current, f'{current} - <a href="/md/meetingdoc.asp?lang=en&amp;parent=T25-SG12-R&amp;PageLB=10"><strong>Next</strong></a>')
    assert looping != last_page
    read_page = fake_client.get_text
    monkeypatch.setattr(fake_client, "get_text", lambda url: looping if url.endswith("&PageLB=10") else read_page(url))

    documents = api.fetch_documents(12, DocType.REPORT, PERIOD)

    assert [document.ref.number for document in documents] == list(range(14, 0, -1))


def test_close_releases_the_store_the_api_owns(tmp_path: Path, fake_client: FakeClient, pooled_connections: Callable[[MetadataStore], int]) -> None:
    """The API releases the metadata store it created and leaves an injected one alone."""
    settings = Settings(cache_dir=tmp_path)
    injected = MetadataStore(settings)
    api = ItuDocuments(settings, client=fake_client, store=injected)
    with injected.session() as session:
        session.exec(select(DocumentRow)).all()
    assert pooled_connections(injected) == 1

    api.close()

    assert pooled_connections(injected) == 1
    owned = ItuDocuments(settings, client=fake_client)
    with owned.store.session() as session:
        session.exec(select(DocumentRow)).all()
    assert pooled_connections(owned.store) == 1
    owned.close()
    assert pooled_connections(owned.store) == 0
    injected.close()


def test_find_documents_filters_by_every_criterion(tmp_path: Path, fake_client: FakeClient) -> None:
    """Every filter of the document search can be combined."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    api.sync_meeting(12, MeetingId.from_code("260609"), PERIOD, (DocType.CONTRIBUTION,))

    records = api.find_documents(
        study_group=12,
        study_period="2025-2028",
        doc_type=DocType.CONTRIBUTION,
        doc_types=(DocType.CONTRIBUTION,),
        meeting="260609",
        question=7,
        source="TU Berlin",
        limit=1,
    )

    assert len(records) == 1
    assert records[0].document_id == "T25-SG12-C-0192"


def test_top_sources_skips_other_meetings(tmp_path: Path, fake_client: FakeClient) -> None:
    """Meetings that are not asked for are left out of the count."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    api.sync_meeting(12, MeetingId.from_code("260609"), PERIOD, (DocType.CONTRIBUTION,))

    assert api.top_sources(study_group=12, meetings=("270119",)) == []


def test_download_writes_a_cached_document_to_an_output_path(tmp_path: Path, fake_client: FakeClient) -> None:
    """A cached document is copied to the requested output path."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    document = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )
    api.cache.store(document, DocFormat.WORD, DocLanguage.ENGLISH, DOCUMENT_BYTES)
    output = tmp_path / "out" / "document.docx"

    path = api.download(document, DocFormat.WORD, DocLanguage.ENGLISH, output_file=output)

    assert path == output
    assert output.read_bytes() == DOCUMENT_BYTES


def test_download_serves_a_cached_document(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document that was downloaded before is served from the cache."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    ref = MeetingId.from_code("261015")
    assert ref.code == "261015"

    document = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    api.cache.store(document, DocFormat.WORD, DocLanguage.ENGLISH, DOCUMENT_BYTES)

    path = api.download(document, DocFormat.WORD, DocLanguage.ENGLISH)

    assert path.read_bytes() == DOCUMENT_BYTES


def test_sync_questions(api: ItuDocuments) -> None:
    """The questions of a study group are stored."""
    assert api.sync_questions(12, PERIOD) == 5


def test_sync_detail(api: ItuDocuments) -> None:
    """The renditions of a document are fetched and stored."""
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    metadata = api.sync_detail(ref)

    assert metadata.files
    assert metadata.files[0].format_code == "MSW"


def test_download_uses_the_cache(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document that was downloaded before is served from the cache."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    assert path.read_bytes() == DOCUMENT_BYTES
    assert client.requested

    again = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH)
    assert again == path
    assert len([url for url in client.requested if url.endswith(".docx")]) == 1
    assert client.login_targets == [client.requested[-1]]


def test_download_writes_to_an_output_path(tmp_path: Path, fake_client: FakeClient) -> None:
    """A document can be written to a chosen path."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )
    output = tmp_path / "out" / "document.docx"

    path = api.download(ref, DocFormat.WORD, DocLanguage.ENGLISH, output_file=output)

    assert path == output
    assert output.read_bytes() == DOCUMENT_BYTES


def test_download_of_an_unavailable_rendition(tmp_path: Path, fake_client: FakeClient) -> None:
    """A rendition that the ITU-T does not offer is reported."""
    client = fake_client
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=client)
    ref = DocumentRef(
        study_period=PERIOD,
        study_group=12,
        doc_type=DocType.TEMPORARY_DOCUMENT,
        number=520,
        subtype="GEN",
        meeting=MeetingId.from_code("261015"),
    )

    with pytest.raises(FileNotFoundError):
        api.download(ref, DocFormat.PDF, DocLanguage.ENGLISH)


@pytest.fixture
def api(tmp_path: Path, fake_client: FakeClient) -> Iterator[ItuDocuments]:
    """Return an API backed by the recorded fixtures."""
    api = ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client)
    yield api
    api.close()


def test_api_context_manager_closes_the_client(tmp_path: Path, fake_client: FakeClient) -> None:
    """The API closes the client it owns."""
    with ItuDocuments(Settings(cache_dir=tmp_path)) as owned:
        assert owned.client is not None
