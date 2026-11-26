"""Tests for the on-disk cache of downloaded documents."""

from __future__ import annotations

from pathlib import Path

from itu_doc_downloader.config.settings import Settings
from itu_doc_downloader.models.documents import DocumentRef, MeetingId, StudyPeriod
from itu_doc_downloader.models.enums import DocFormat, DocLanguage, DocType
from itu_doc_downloader.storage.files import FileCache

PERIOD = StudyPeriod(start_year=2025, end_year=2028)
REF = DocumentRef(
    study_period=PERIOD,
    study_group=12,
    doc_type=DocType.TEMPORARY_DOCUMENT,
    number=520,
    subtype="GEN",
    meeting=MeetingId.from_code("261015"),
)


def test_path_of_a_rendition(tmp_path: Path) -> None:
    """A rendition is cached under the identifier of its document."""
    cache = FileCache(Settings(cache_dir=tmp_path))

    path = cache.path_for(REF, DocFormat.PDF, DocLanguage.ENGLISH)

    assert path == tmp_path / "files" / "T25-SG12-261015-TD-GEN-0520" / "PDF-E.pdf"


def test_store_and_load_a_rendition(tmp_path: Path) -> None:
    """A stored rendition is read back."""
    cache = FileCache(Settings(cache_dir=tmp_path))

    assert not cache.has(REF, DocFormat.WORD, DocLanguage.ENGLISH)

    path = cache.store(REF, DocFormat.WORD, DocLanguage.ENGLISH, b"content")

    assert path.read_bytes() == b"content"
    assert cache.has(REF, DocFormat.WORD, DocLanguage.ENGLISH)
    assert cache.load(REF, DocFormat.WORD, DocLanguage.ENGLISH) == b"content"


def test_load_a_missing_rendition(tmp_path: Path) -> None:
    """A rendition that was never stored yields nothing."""
    cache = FileCache(Settings(cache_dir=tmp_path))

    assert cache.load(REF, DocFormat.PDF, DocLanguage.FRENCH) is None
