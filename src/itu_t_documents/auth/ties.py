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
recorded request/response chain. :mod:`itu_t_documents.auth.forms` reads the
forms and messages the handshake is made of.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx

from itu_t_documents.auth.forms import (
    SAML_CONSUMER_MARKER,
    SAML_PROFILE_MARKERS,
    SAML_REQUEST_FIELD,
    SAML_RESPONSE_FIELD,
    SSO_REQUEST_URL,
    extract_apmui_message,
    find_profile_form,
    find_saml_form,
    sso_request_url,
)
from itu_t_documents.auth.forms import (
    _iter_forms as _iter_forms_from_forms,
)
from itu_t_documents.errors import AuthenticationError, ScrapingError

#: Logon endpoint of the ITU-T identity provider.
LOGON_URL = "https://login.itu.int/my.policy"

#: Resource the session is opened for when no document is named. The access
#: policy only opens a session for a protected resource, so the probe points at
#: a document file that does not exist.
SESSION_PROBE_URL = "https://www.itu.int/dms_ties/itu-t/md/25/sg12/r/T25-SG12-R-0000!!MSW-E.docx"

#: Maximum number of redirects and SAML handovers followed during one login.
_MAX_HOPS = 8

#: HTTP status codes that carry a redirect.
_REDIRECT_STATUS = {301, 302, 303, 307, 308}

__all__ = [
    "LOGON_URL",
    "SAML_CONSUMER_MARKER",
    "SAML_PROFILE_MARKERS",
    "SAML_REQUEST_FIELD",
    "SAML_RESPONSE_FIELD",
    "SESSION_PROBE_URL",
    "SSO_REQUEST_URL",
    "AuthenticationError",
    "ScrapingError",
    "TiesAuthenticator",
    "extract_apmui_message",
    "find_profile_form",
    "find_saml_form",
    "sso_request_url",
]


def _iter_forms(page_html: str) -> Iterator[tuple[str, dict[str, str]]]:
    """Yield the forms of a TIES page; kept importable here for compatibility."""
    yield from _iter_forms_from_forms(page_html)


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
        else:
            raise AuthenticationError("TIES login did not complete within the allowed number of hops")

        if not reached_consumer:
            raise AuthenticationError("TIES login did not reach the assertion consumer service")
