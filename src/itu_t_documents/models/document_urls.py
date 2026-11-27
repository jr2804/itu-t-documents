"""URLs of the ITU-T document management system.

Kept apart from the identifiers so that the domain model and the URL builders
share the one wire format without importing each other.
"""

from __future__ import annotations

#: Root of the ITU-T web site.
BASE_URL = "https://www.itu.int"

#: The meeting document application and the language of the scraped pages.
MEETING_DOC_URL = f"{BASE_URL}/md/meetingdoc.asp"
LANGUAGE = "en"


def detail_url(document_id: str) -> str:
    """Return the URL of the detail page of a document.

    Args:
        document_id: The DMS identifier of the document.

    Returns:
        The absolute URL of the detail page.
    """
    return f"{MEETING_DOC_URL}?lang={LANGUAGE}&parent={document_id}"
