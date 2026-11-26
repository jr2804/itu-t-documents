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
    find_saml_form,
)

SAML_REQUEST_PAGE = f"""<html><body><form action="https://login.itu.int/saml/idp/profile/redirectorpost/sso">
<input type="hidden" name="{SAML_REQUEST_FIELD}" value="PHNhbWw+"/></form></body></html>"""

SAML_RESPONSE_PAGE = """<html><body><form action="https://auth.itu.int/saml/idp/profile/post/acs">
<input type="hidden" name="SAMLResponse" value="PHNhbWw+"/>
<input type="hidden" name="RelayState" value=""/></form></body></html>"""

LOGON_PAGE = '<html><body><form id="auth_form"></form></body></html>'

BLOCKED_PAGE = """<html><body><script>appLoader.configure({
"pageType": "messageBox",
"messageBox": { "config": { "title": "Your account has been blocked.",
"message": "Please contact support to unlock your account" } } });</script></body></html>"""


def _handler(request: httpx.Request) -> httpx.Response:
    """Simulate the ITU-T access policy and its identity provider."""
    url = str(request.url)
    if request.method == "GET" and url.startswith("https://www.itu.int/dms_"):
        return httpx.Response(302, headers={"location": "https://auth.itu.int/F5Networks-SSO-Req?SSO_ORIG_URI=x"})
    if request.method == "GET" and "F5Networks-SSO-Req" in url:
        return httpx.Response(302, headers={"location": "https://auth.itu.int/my.policy"})
    if request.method == "GET" and url == "https://auth.itu.int/my.policy":
        return httpx.Response(200, text=SAML_REQUEST_PAGE)
    if request.method == "POST" and "redirectorpost" in url:
        return httpx.Response(200, text=LOGON_PAGE)
    if request.method == "POST" and url == LOGON_URL:
        return httpx.Response(200, text=SAML_RESPONSE_PAGE)
    if request.method == "POST" and "post/acs" in url:
        return httpx.Response(302, headers={"location": "https://www.itu.int/dms_inf/doc.pdf"})
    if request.method == "GET" and url.startswith("https://www.itu.int/dms_"):
        return httpx.Response(200, content=b"document")
    return httpx.Response(500)


def _client() -> httpx.Client:
    """Return a client wired to the simulated ITU-T pages."""
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
