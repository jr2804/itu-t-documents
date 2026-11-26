"""Parser for the ITU-T document detail pages.

The detail page of a document lists every available rendition in a table with
the columns *language*, *format*, *size*, *posted* and *number*. The download
URL of a rendition carries the format and the language code, e.g.
``…/T25-SG12-261015-TD-GEN-0520!!MSW-E.docx``.
"""

from __future__ import annotations

import re
from datetime import date

from itu_doc_downloader.models.documents import DocumentFile
from itu_doc_downloader.scraping.pages import parse_page

#: Pattern of the format and language suffix of a download URL.
_SUFFIX_RE = re.compile(r"!!(?P<format>[A-Z0-9]+)-(?P<language>[A-Z])\.(?P<extension>[a-z0-9]+)$")

#: Pattern of the size column, e.g. ``46104 bytes``.
_SIZE_RE = re.compile(r"(?P<size>\d[\d\s.,]*)\s*bytes", re.IGNORECASE)

#: Pattern of the title heading, e.g. ``[520-GEN] Draft agenda for WP1/12``.
_TITLE_RE = re.compile(r"\[(?P<number>[^\]]+)\]\s*(?P<title>.*)", re.DOTALL)


def parse_files(page_html: str, base_url: str = "https://www.itu.int") -> list[DocumentFile]:
    """Parse the available renditions of a document.

    Args:
        page_html: The HTML of the detail page.
        base_url: The root the relative download URLs are resolved against.

    Returns:
        One entry per available rendition.
    """
    tree = parse_page(page_html)
    if tree is None:
        return []
    files: list[DocumentFile] = []
    seen: set[str] = set()
    for row in tree.xpath("//tr[count(td) > 1][.//a[contains(@href, '!!')]]"):
        cells = row.xpath("./td")
        for link in row.xpath(".//a[contains(@href, '!!')]"):
            href = link.get("href") or ""
            match = _SUFFIX_RE.search(href)
            if match is None:
                continue
            url = base_url + href if href.startswith("/") else href
            if url in seen:
                continue
            seen.add(url)
            files.append(
                DocumentFile(
                    format_code=match["format"],
                    language_code=match["language"],
                    size_bytes=_parse_size(cells[2].text_content()) if len(cells) > 2 else None,
                    posted=_parse_date(cells[3].text_content()) if len(cells) > 3 else None,
                    url=url,
                )
            )
    return files


def _parse_size(text: str) -> int | None:
    """Parse the size column of the rendition table."""
    match = _SIZE_RE.search(re.sub(r"\s+", " ", text))
    if match is None:
        return None
    digits = re.sub(r"[^\d]", "", match.group("size"))
    return int(digits) if digits else None


def _parse_date(text: str) -> date | None:
    """Parse the posted date of a rendition."""
    text = re.sub(r"\s+", " ", text).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_title(page_html: str) -> str:
    """Parse the title heading of a document detail page.

    Args:
        page_html: The HTML of the detail page.

    Returns:
        The title of the document, without the document number.
    """
    tree = parse_page(page_html)
    if tree is None:
        return ""
    for cell in tree.xpath("//td[@colspan]"):
        text = re.sub(r"\s+", " ", cell.text_content()).strip()
        match = _TITLE_RE.match(text)
        if match is not None and match.group("title").strip():
            return match.group("title").strip()
    return ""
