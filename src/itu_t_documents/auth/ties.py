"""TIES authentication for the ITU-T document management system.

The ITU-T DMS is protected by the F5 BIG-IP access policy at ``auth.itu.int``
and delegates authentication to the SAML identity provider at ``login.itu.int``.
A complete login consists of four steps:

1. Requesting a protected document. The access policy answers with a redirect
   to ``auth.itu.int/F5Networks-SSO-Req`` which in turn serves a page carrying
   a SAML ``AuthnRequest`` for the identity provider.
2. Posting that ``SAMLRequest`` to ``login.itu.int``. The identity provider
   answers with its logon page.
3. Posting the TIES user name and password to the logon page. On success the
   identity provider answers with a SAML ``Response`` for the assertion
   consumer service of ``www.itu.int``.
4. Posting the ``SAMLResponse`` to the assertion consumer service, which
   establishes the session cookie on ``www.itu.int``.

The steps were reverse engineered from the live pages; see ``docs/`` for the
recorded request/response chain.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Iterator

import httpx
from lxml import html

from itu_t_documents.errors import AuthenticationError

#: Logon endpoint of the ITU-T identity provider.
LOGON_URL = "https://login.itu.int/my.policy"

#: Endpoint of the access policy that starts the single sign-on handshake.
SSO_REQUEST_URL = "https://auth.itu.int/F5Networks-SSO-Req"

#: Resource the session is opened for when no document is named. The access
#: policy only opens a session for a protected resource, so the probe points at
#: a document file that does not exist.
SESSION_PROBE_URL = "https://www.itu.int/dms_ties/itu-t/md/25/sg12/r/T25-SG12-R-0000!!MSW-E.docx"

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

#: Maximum number of redirects and SAML handovers followed during one login.
_MAX_HOPS = 8

#: HTTP status codes that carry a redirect.
_REDIRECT_STATUS = {301, 302, 303, 307, 308}


class TiesAuthenticator:
    """Performs the TIES login against the ITU-T DMS and keeps the session alive."""

    def __init__(self, client: httpx.Client, username: str, password: str) -> None:
        """Create an authenticator.

        Args:
            client: The HTTP client used for the whole handshake. It must follow
                redirects and keep cookies.
            username: The TIES account name or e-mail address.
            password: The TIES account password.
        """
        self._client = client
        self._username = username
        self._password = password
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        """Whether a successful login has been performed on this session."""
        return self._authenticated

    def login_for(self, url: str) -> None:
        """Authenticate so that ``url`` becomes accessible.

        The access policy needs to know which resource is requested, therefore
        the handshake is started by requesting the protected URL itself. When
        the URL turns out to be public, the handshake is started at the single
        sign-on endpoint of the access policy instead.

        Args:
            url: The protected URL that should become accessible.

        Raises:
            AuthenticationError: When the identity provider rejects the
                credentials or the handshake cannot be completed.
        """
        self._authenticated = False
        response = self._client.get(url, follow_redirects=True)
        saml_form = find_saml_form(response.text, SAML_REQUEST_FIELD)
        if saml_form is None:
            response = self._client.get(sso_request_url(url), follow_redirects=True)
            saml_form = find_saml_form(response.text, SAML_REQUEST_FIELD)
        if saml_form is None:
            raise AuthenticationError(f"no TIES login form found while requesting {url}")
        action, fields = saml_form
        idp_response = self._client.post(
            response.url.join(action),
            data=fields,
            headers={"Referer": str(response.url)},
            follow_redirects=True,
        )
        credentials_response = self._client.post(
            LOGON_URL,
            data={"username": self._username, "password": self._password},
            headers={"Referer": str(idp_response.url)},
            follow_redirects=False,
        )
        self._complete_handshake(credentials_response)
        self._authenticated = True

    def _complete_handshake(self, response: httpx.Response) -> None:
        """Follow redirects and SAML handovers until the session is established.

        Args:
            response: The response of the credential submission.

        Raises:
            AuthenticationError: When the identity provider rejected the
                credentials or the handshake did not finish.
        """
        current = response
        reached_consumer = False
        for _ in range(_MAX_HOPS):
            if current.status_code in _REDIRECT_STATUS:
                location = current.headers.get("location")
                if not location:
                    raise AuthenticationError("TIES login failed: the access policy redirected without a target")
                current = self._client.get(current.url.join(location), follow_redirects=False)
                continue

            message = extract_apmui_message(current.text)
            if message is not None:
                raise AuthenticationError(f"TIES login failed: {message}")

            form = find_profile_form(current.text)
            if form is None:
                break
            action, fields = form
            current = self._client.post(
                current.url.join(action),
                data=fields,
                headers={"Referer": str(current.url)},
                follow_redirects=False,
            )
            if SAML_CONSUMER_MARKER in action:
                # The assertion consumer service accepted the response, the
                # session is established. What the resource answers afterwards
                # does not say anything about the login.
                reached_consumer = True
        else:  # pragma: no cover - defensive, the hop budget is generous
            raise AuthenticationError("TIES login did not complete within the allowed number of hops")

        if not reached_consumer:
            raise AuthenticationError("TIES login did not reach the assertion consumer service")


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
    """Yield ``(action, fields)`` for every form found in ``page_html``."""
    try:
        tree = html.fromstring(page_html)
    except ValueError:  # pragma: no cover - defensive, malformed markup
        return
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
