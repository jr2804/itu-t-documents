"""Helpers for the ITU-T pages.

The ITU-T answers some requests with an empty body and a status of 200. The
parsers therefore have to cope with a page that holds no markup at all.
"""

from __future__ import annotations

import re

from lxml import html
from lxml.html import HtmlElement

from itu_t_documents.errors import ScrapingError


def scraping_error(page: str, text: str) -> ScrapingError:
    """Build the error for scraped text that cannot be read.

    The text is untrusted input, so only a short, whitespace-normalised
    excerpt is kept in the message.
    """
    excerpt = re.sub(r"\s+", " ", text).strip()[:200]
    return ScrapingError(f"cannot read {page}: {excerpt!r}")


def clean_text(text: str) -> str:
    """Normalise whitespace of a scraped text fragment."""
    return re.sub(r"\s+", " ", text).strip()


def parse_page(page_html: str) -> HtmlElement | None:
    """Parse a page of the ITU-T web site.

    Args:
        page_html: The HTML of the page.

    Returns:
        The parsed page, or ``None`` when the page holds no markup.
    """
    if not page_html.strip():
        return None
    try:
        return html.fromstring(page_html)
    except (html.etree.ParserError, ValueError):
        return None
