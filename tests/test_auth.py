"""Tests for the TIES authentication handshake."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx
import pytest

from itu_t_documents.auth.ties import (
    LOGON_URL,
    SAML_REQUEST_FIELD,
    SAML_RESPONSE_FIELD,
    AuthenticationError,
    TiesAuthenticator,
    _iter_forms,
    extract_apmui_message,
    find_profile_form,
    find_saml_form,
    sso_request_url,
)
from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import ScrapingError
from itu_t_documents.models.documents import MeetingId
from itu_t_documents.scraping import meetings

SAML_REQUEST_PAGE = f"""<html><body><form action="https://login.itu.int/saml/idp/profile/redirectorpost/sso">
<input type="hidden" name="{SAML_REQUEST_FIELD}" value="PHNhbWw+"/></form></body></html>"""

SAML_RESPONSE_PAGE = """<html><body><form action="https://auth.itu.int/saml/sp/profile/post/acs">
<input type="hidden" name="SAMLResponse" value="PHNhbWw+"/>
<input type="hidden" name="RelayState" value=""/></form></body></html>"""

LOGON_PAGE = '<html><body><form id="auth_form"></form></body></html>'

DUMMY_PAGE = """<html><body onload="document.forms[0].submit()">
<form method="POST" action="https://login.itu.int/saml/idp/profile/redirectorpost/sso">
<input type="hidden" name="dummy" value="92b6ecc7"/></form></body></html>"""

BLOCKED_PAGE = """<html><body><script>appLoader.configure({
"pageType": "messageBox",
"messageBox": { "config": { "title": "Your account has been blocked.",
"message": "Please contact support to unlock your account" } } });</script></body></html>"""


@dataclass
class FakeIdentityProvider:
    """The state and the simulated responses of the ITU-T identity provider."""

    authenticated: bool = False
    posts: list[str] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Simulate the ITU-T access policy and its identity provider."""
        url = str(request.url)
        if request.method == "GET" and url.startswith("https://www.itu.int/dms_"):
            if self.authenticated:
                return httpx.Response(200, content=b"document")
            return httpx.Response(302, headers={"location": "https://auth.itu.int/F5Networks-SSO-Req?SSO_ORIG_URI=x"})
        if request.method == "GET" and "F5Networks-SSO-Req" in url:
            return httpx.Response(302, headers={"location": "https://auth.itu.int/my.policy"})
        if request.method == "GET" and url == "https://auth.itu.int/my.policy":
            return httpx.Response(200, text=SAML_REQUEST_PAGE)
        if request.method == "POST" and "redirectorpost" in url:
            # The first post carries the SAML request, the second one the dummy value.
            self.posts.append(url)
            if len(self.posts) == 1:
                return httpx.Response(200, text=LOGON_PAGE)
            if len(self.posts) == 2:
                return httpx.Response(200, text=DUMMY_PAGE)
            return httpx.Response(200, text=SAML_RESPONSE_PAGE)
        if request.method == "POST" and url == LOGON_URL:
            return httpx.Response(200, text=DUMMY_PAGE)
        if request.method == "POST" and "post/acs" in url:
            self.authenticated = True
            return httpx.Response(302, headers={"location": "https://www.itu.int/dms_inf/doc.pdf"})
        return httpx.Response(500)


def test_find_saml_form_returns_the_action_and_fields() -> None:
    """The SAML form of a page is found with its action and fields."""
    form = find_saml_form(SAML_REQUEST_PAGE, SAML_REQUEST_FIELD)

    assert form is not None
    action, fields = form
    assert action == "https://login.itu.int/saml/idp/profile/redirectorpost/sso"
    assert fields[SAML_REQUEST_FIELD] == "PHNhbWw+"


def test_find_saml_form_returns_none_without_the_field() -> None:
    """A page without the requested field yields no form."""
    assert find_saml_form(LOGON_PAGE, SAML_REQUEST_FIELD) is None


def test_sso_request_url_carries_the_target() -> None:
    """The single sign-on URL carries the base64 encoded target."""
    url = sso_request_url("https://www.itu.int/md/")

    assert url.startswith("https://auth.itu.int/F5Networks-SSO-Req?SSO_ORIG_URI=")
    assert "aHR0cHM6Ly93d3cuaXR1LmludC9tZC8" in url


def test_find_profile_form_matches_both_endpoints() -> None:
    """The profile form of the identity provider and of the assertion consumer are found."""
    idp_page = '<form action="/saml/idp/profile/redirectorpost/sso"><input name="dummy" value="1"/></form>'
    acs_page = '<form action="https://auth.itu.int/saml/sp/profile/post/acs"><input name="SAMLResponse" value="2"/></form>'

    assert find_profile_form(idp_page) is not None
    assert find_profile_form(acs_page) is not None
    assert find_profile_form('<form action="/md/other"></form>') is None


def test_extract_apmui_message() -> None:
    """The message of an access policy error page is extracted."""
    assert extract_apmui_message(BLOCKED_PAGE) == ("Your account has been blocked.: Please contact support to unlock your account")


def test_extract_apmui_message_without_a_message() -> None:
    """A page without a message box yields no message."""
    assert extract_apmui_message(LOGON_PAGE) is None


def test_login_completes_the_handshake() -> None:
    """A successful login walks through the whole SAML chain."""
    client = _client()
    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    authenticator.login_for("https://www.itu.int/dms_inf/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx")

    assert authenticator.is_authenticated
    client.close()


def test_login_reports_a_blocked_account() -> None:
    """A rejected login is reported with the message of the access policy."""
    provider = FakeIdentityProvider()

    def blocked(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(200, text=BLOCKED_PAGE)
        return provider.handler(request)

    client = httpx.Client(transport=httpx.MockTransport(blocked), follow_redirects=True)
    authenticator = TiesAuthenticator(client, "you@example.org", "wrong")

    with pytest.raises(AuthenticationError, match="blocked"):
        authenticator.login_for("https://www.itu.int/dms_inf/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx")

    assert not authenticator.is_authenticated
    client.close()


def test_login_page_with_broken_markup_is_reported() -> None:
    """Malformed HTML from the identity provider is a scraping error."""
    with pytest.raises(ScrapingError, match="cannot read TIES login page"):
        list(_iter_forms("<html"))


def test_handshake_with_too_many_hops_is_reported() -> None:
    """An access policy that never finishes is not treated as a login."""

    def looping(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": str(request.url)})

    client = httpx.Client(transport=httpx.MockTransport(looping), follow_redirects=False)
    authenticator = TiesAuthenticator(client, "you@example.org", "secret")
    response = httpx.Response(302, request=httpx.Request("POST", LOGON_URL), headers={"location": "https://auth.itu.int/loop"})

    with pytest.raises(AuthenticationError, match="did not complete within"):
        authenticator._complete_handshake(response)

    client.close()


def _client() -> httpx.Client:
    """Return a client wired to the simulated ITU-T pages."""
    provider = FakeIdentityProvider()
    return httpx.Client(transport=httpx.MockTransport(provider.handler), follow_redirects=True)


def test_login_reports_a_missing_login_form() -> None:
    """A protected page without a login form is reported."""

    def plain(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>nothing</body></html>")

    client = httpx.Client(transport=httpx.MockTransport(plain), follow_redirects=True)
    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError, match="no TIES login form"):
        authenticator.login_for("https://www.itu.int/dms_inf/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx")

    client.close()


def test_authenticator_reports_a_server_error() -> None:
    """A server error during the handshake is reported."""

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = httpx.Client(transport=httpx.MockTransport(failing), follow_redirects=True)

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_authenticator_follows_a_redirect_without_a_location() -> None:
    """A redirect without a target ends the handshake."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(302)
        return httpx.Response(200, text=f'<form action="x"><input name="{SAML_REQUEST_FIELD}" value="y"/></form>')

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_authenticator_reports_a_failed_status() -> None:
    """A failing status code is reported."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(403, text="denied")
        return httpx.Response(200, text=f'<form action="x"><input name="{SAML_REQUEST_FIELD}" value="y"/></form>')

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError, match="assertion consumer service"):
        authenticator.login_for("https://www.itu.int/md/")

    client.close()


def test_saml_response_form_is_found() -> None:
    """The SAML response form of a page is found."""
    page = f'<form action="https://auth.itu.int/acs"><input name="{SAML_RESPONSE_FIELD}" value="z"/></form>'

    form = find_saml_form(page, SAML_RESPONSE_FIELD)

    assert form is not None
    assert form[0] == "https://auth.itu.int/acs"


def test_date_of_a_meeting_is_read_from_the_page() -> None:
    """The start date of a meeting is part of its information."""
    info = meetings.MeetingInfo(MeetingId.from_code("261015"), "E-Meeting", date(2026, 10, 15), date(2026, 10, 16))

    assert info.end_date == date(2026, 10, 16)


def test_authenticate_uses_the_credentials(tmp_path: Path) -> None:
    """A login is performed when credentials are configured."""
    Settings(cache_dir=tmp_path, ties_username="you@example.org", ties_password="secret")
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)), follow_redirects=True)

    authenticator = TiesAuthenticator(client, "you@example.org", "secret")
    assert authenticator.is_authenticated is False
    client.close()
