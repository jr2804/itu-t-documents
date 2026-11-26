"""Tests for the TIES authentication handshake."""

from __future__ import annotations

import httpx
import pytest

from itu_doc_downloader.auth.ties import (
    LOGON_URL,
    SAML_REQUEST_FIELD,
    AuthenticationError,
    TiesAuthenticator,
    extract_apmui_message,
    find_profile_form,
    find_saml_form,
    sso_request_url,
)

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


#: The requests that were posted to the SAML profile endpoints.
_POSTS: list[str] = []

#: Whether the assertion consumer service has accepted a SAML response.
_AUTHENTICATED = False


def _handler(request: httpx.Request) -> httpx.Response:
    """Simulate the ITU-T access policy and its identity provider."""
    global _AUTHENTICATED  # noqa: PLW0603
    url = str(request.url)
    if request.method == "GET" and url.startswith("https://www.itu.int/dms_"):
        if _AUTHENTICATED:
            return httpx.Response(200, content=b"document")
        return httpx.Response(302, headers={"location": "https://auth.itu.int/F5Networks-SSO-Req?SSO_ORIG_URI=x"})
    if request.method == "GET" and "F5Networks-SSO-Req" in url:
        return httpx.Response(302, headers={"location": "https://auth.itu.int/my.policy"})
    if request.method == "GET" and url == "https://auth.itu.int/my.policy":
        return httpx.Response(200, text=SAML_REQUEST_PAGE)
    if request.method == "POST" and "redirectorpost" in url:
        # The first post carries the SAML request, the second one the dummy value.
        _POSTS.append(url)
        if len(_POSTS) == 1:
            return httpx.Response(200, text=LOGON_PAGE)
        if len(_POSTS) == 2:
            return httpx.Response(200, text=DUMMY_PAGE)
        return httpx.Response(200, text=SAML_RESPONSE_PAGE)
    if request.method == "POST" and url == LOGON_URL:
        return httpx.Response(200, text=DUMMY_PAGE)
    if request.method == "POST" and "post/acs" in url:
        _AUTHENTICATED = True
        return httpx.Response(302, headers={"location": "https://www.itu.int/dms_inf/doc.pdf"})
    if request.method == "GET" and url.startswith("https://www.itu.int/dms_"):
        return httpx.Response(200, content=b"document")
    return httpx.Response(500)


def _client() -> httpx.Client:
    """Return a client wired to the simulated ITU-T pages."""
    global _AUTHENTICATED  # noqa: PLW0603
    _AUTHENTICATED = False
    _POSTS.clear()
    return httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=True)


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
    client = _client()

    def blocked(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url) == LOGON_URL:
            return httpx.Response(200, text=BLOCKED_PAGE)
        return _handler(request)

    client = httpx.Client(transport=httpx.MockTransport(blocked), follow_redirects=True)
    authenticator = TiesAuthenticator(client, "you@example.org", "wrong")

    with pytest.raises(AuthenticationError, match="blocked"):
        authenticator.login_for("https://www.itu.int/dms_inf/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx")

    assert not authenticator.is_authenticated
    client.close()


def test_login_reports_a_missing_login_form() -> None:
    """A protected page without a login form is reported."""

    def plain(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>nothing</body></html>")

    client = httpx.Client(transport=httpx.MockTransport(plain), follow_redirects=True)
    authenticator = TiesAuthenticator(client, "you@example.org", "secret")

    with pytest.raises(AuthenticationError, match="no TIES login form"):
        authenticator.login_for("https://www.itu.int/dms_inf/itu-t/md/25/sg12/r/T25-SG12-R-0001!!MSW-E.docx")

    client.close()
