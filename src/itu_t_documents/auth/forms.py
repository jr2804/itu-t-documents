"""Find the SAML forms and messages in the pages of the TIES handshake."""

from __future__ import annotations

import base64
import re
from collections.abc import Iterator

from lxml import html

from itu_t_documents.errors import ScrapingError

#: Endpoint of the access policy that starts the single sign-on handshake.
SSO_REQUEST_URL = "https://auth.itu.int/F5Networks-SSO-Req"

#: Name of the hidden form field carrying a SAML request.
SAML_REQUEST_FIELD = "SAMLRequest"

#: Name of the hidden form field carrying a SAML response.
SAML_RESPONSE_FIELD = "SAMLResponse"

#: Markers of the SAML profile endpoints. The identity provider serves the
#: login on ``login.itu.int`` (``/saml/idp/profile/``), the assertion consumer
#: service on ``auth.itu.int`` (``/saml/sp/profile/``).
SAML_PROFILE_MARKERS = ("/saml/", "/profile/")

#: Marker of the assertion consumer service, which accepts the SAML response.
SAML_CONSUMER_MARKER = "/saml/sp/profile/"


def sso_request_url(target: str) -> str:
    """Return the single sign-on URL of the access policy for a resource.

    Args:
        target: The protected resource the session is opened for.

    Returns:
        The absolute URL of the single sign-on endpoint.
    """
    encoded = base64.b64encode(target.encode("utf-8")).decode("ascii")
    return f"{SSO_REQUEST_URL}?SSO_ORIG_URI={encoded}"


def find_saml_form(page_html: str, field: str) -> tuple[str, dict[str, str]] | None:
    """Return the first form on the page that carries ``field``.

    Args:
        page_html: The HTML of the page.
        field: The name of the hidden SAML field to look for.

    Returns:
        The form action and its fields, or ``None`` when the page has no such form.
    """
    for action, fields in _iter_forms(page_html):
        if field in fields:
            return action, fields
    return None


def find_profile_form(page_html: str) -> tuple[str, dict[str, str]] | None:
    """Return the first form on the page that points at a SAML profile endpoint.

    The identity provider answers a successful login with pages that submit
    themselves: first a form that hands a ``dummy`` value back to the profile
    endpoint, then a form that posts the SAML response to the assertion
    consumer service.

    Args:
        page_html: The HTML of the page.

    Returns:
        The form action and its fields, or ``None`` when the page has no such form.
    """
    for action, fields in _iter_forms(page_html):
        if all(marker in action for marker in SAML_PROFILE_MARKERS):
            return action, fields
    return None


def _iter_forms(page_html: str) -> Iterator[tuple[str, dict[str, str]]]:
    """Yield ``(action, fields)`` for every form found in ``page_html``.

    Raises:
        ScrapingError: When the identity provider answers unreadable markup.
    """
    try:
        tree = html.fromstring(page_html)
    except (html.etree.ParserError, ValueError) as error:
        raise ScrapingError(f"cannot read TIES login page: {page_html[:200]!r}") from error
    for form in tree.xpath("//form"):
        fields = {node.get("name"): node.get("value") or "" for node in form.xpath(".//input[@name]")}
        yield form.get("action") or "", fields


def extract_apmui_message(page_html: str) -> str | None:
    """Extract the user facing message of an F5 access policy error page.

    Args:
        page_html: The HTML of the page.

    Returns:
        The message shown to the user, or ``None`` when the page carries none.
    """
    index = page_html.find('"messageBox"')
    section = page_html[index : index + 3000] if index >= 0 else ""
    title = re.search(r'"title":\s*"((?:[^"\\]|\\.)*)"', section)
    message = re.search(r'"message":\s*"((?:[^"\\]|\\.)*)"', section)
    parts = [part.group(1) for part in (title, message) if part is not None]
    if not parts:
        return None
    return ": ".join(parts)
