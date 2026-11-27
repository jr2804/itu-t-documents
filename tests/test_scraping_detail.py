"""Tests for the parser of the document detail pages."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from itu_t_documents.scraping import detail, listing


def test_parse_detail_page(fixtures_dir: Path) -> None:
    """A detail page yields the available renditions of a document."""
    page = _read(fixtures_dir, "detail_temporary_document.html")

    files = detail.parse_files(page)

    assert len(files) == 1
    rendition = files[0]
    assert rendition.format_code == "MSW"
    assert rendition.language_code == "E"
    assert rendition.size_bytes == 46104
    assert rendition.posted == date(2026, 10, 9)
    assert rendition.url == ("https://www.itu.int/dms_inf/itu-t/md/25/sg12/td/261015/GEN/T25-SG12-261015-TD-GEN-0520!!MSW-E.docx")


def test_parse_detail_page_title(fixtures_dir: Path) -> None:
    """A detail page yields the title of a document."""
    page = _read(fixtures_dir, "detail_temporary_document.html")

    assert detail.parse_title(page) == "Draft agenda for WP1/12: Terminals and multimedia subjective assessment"


def test_parse_detail_page_of_a_revised_document(fixtures_dir: Path) -> None:
    """A revised document yields its original and its revisions."""
    page = _read(fixtures_dir, "detail_revised_contribution.html")

    files = detail.parse_files(page)

    assert len(files) == 7
    revisions = [file for file in files if file.revision == 1]
    assert {file.language_code for file in revisions} == {"A", "C", "E", "F", "R", "S"}
    originals = [file for file in files if file.revision is None]
    assert len(originals) == 1
    assert originals[0].language_code == "E"
    assert originals[0].url == "https://www.itu.int/dms_ties/itu-t/md/25/sg02/c/T25-SG02-C-0001!!MSW-E.docx"


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_parse_files_ignores_a_duplicate_url() -> None:
    """The same rendition is only reported once."""
    link = '<a href="/dms_inf/x!!MSW-E.docx">Word</a>'
    page = (
        f"<html><body><table><tr><td>English</td><td>{link}</td><td>1 bytes</td><td>2026-01-01</td></tr>"
        f"<tr><td>English</td><td>{link}</td><td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1


def test_parse_files_ignores_a_link_without_a_format() -> None:
    """A link that carries no format suffix is ignored."""
    page = (
        "<html><body><table><tr><td>English</td>"
        '<td><a href="/dms_inf/x!!ABC">Word</a><a href="/dms_inf/y!!MSW-E.docx">Word</a></td>'
        "<td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1
    assert files[0].url.endswith("!!MSW-E.docx")


def test_parse_files_keeps_an_absolute_url() -> None:
    """An absolute download URL is kept as it is."""
    page = (
        "<html><body><table><tr><td>English</td>"
        '<td><a href="https://www.itu.int/dms_inf/x!!MSW-E.docx">Word</a></td>'
        "<td>1 bytes</td><td>2026-01-01</td></tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert files[0].url == "https://www.itu.int/dms_inf/x!!MSW-E.docx"


def test_parse_detail_page_without_files() -> None:
    """A detail page without renditions yields no file."""
    assert detail.parse_files("<html><body>no files</body></html>") == []


def test_parse_detail_page_without_a_title() -> None:
    """A detail page without a heading yields no title."""
    assert detail.parse_title("<html><body>nothing</body></html>") == ""


def test_parse_date_of_an_unreadable_value() -> None:
    """A date that cannot be read is reported as missing."""
    assert listing._parse_date("not a date") is None


def test_parse_date_of_a_rendition_that_cannot_be_read() -> None:
    """A posted date that cannot be read is reported as missing."""
    assert detail._parse_date("not a date") is None


def test_parse_files_ignores_a_link_without_a_suffix() -> None:
    """A link that carries no format suffix is ignored."""
    page = '<html><body><table><tr><td><a href="/dms_inf/itu-t/md/x">Word</a></td></tr></table></body></html>'

    assert detail.parse_files(page) == []


def test_parse_size_of_an_unreadable_value() -> None:
    """A size that cannot be read is reported as missing."""
    assert detail._parse_size("unknown") is None


def test_parse_files_reads_every_rendition() -> None:
    """Every rendition of a row is read."""
    page = (
        "<html><body><table><tr>"
        '<td>English</td><td><a href="/dms_inf/x!!MSW-E.docx">Word</a></td>'
        "<td>46104 bytes</td><td>2026-10-09</td><td>[520-GEN]</td>"
        "</tr></table></body></html>"
    )

    files = detail.parse_files(page)

    assert len(files) == 1
    assert files[0].size_bytes == 46104
    assert files[0].posted == date(2026, 10, 9)
