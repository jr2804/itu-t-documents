---
title: The ITU-T Document Management System
---

The ITU-T publishes the documents of its study group meetings in the Document
Management System (DMS) on `www.itu.int`. This page records the URL layout,
the numbering scheme and the authentication chain that were reverse engineered
from the live pages. It is the reference the package is built on.

## Document identifiers

A document is addressed by study period, study group, document type and an
increasing number:

```text
T25-SG12-C-0192               contribution
T25-SG12-261015-TD-GEN-0520   temporary document
T25-SG12-COL-0001             collective letter
T25-SG12-R-0001               report
```

| Part | Meaning | Example |
|------|---------|---------|
| `T25` | Study period, `T` plus the two-digit start year | `2025-2028` |
| `SG12` | Study group, zero padded to two digits | `12`, `5` becomes `SG05` |
| `261015` | Meeting, the start date as `YYMMDD` | 15 October 2026 |
| `TD` | Document type | see below |
| `GEN` | Sub-type of a temporary document | general |
| `0520` | Number of the document, zero padded to four digits | `520` |

The document types are `C` (contribution), `TD` (temporary document), `COL`
(collective letter) and `R` (report).

Single digit study groups are written with a leading zero: study group 5
appears as `SG05` in every identifier and in every path, and the study group
home page lives under `/studygroups/2025-2028/05/`. The `net4` applications
are the exception, they take the plain number as `Group=5`.

Contributions, collective letters and reports are numbered consecutively
across the whole study period, so their identifier carries no meeting. A
temporary document belongs to one meeting and therefore embeds its date and a
sub-type. The number of a contribution is unique inside a study group, which
means the meeting of a contribution is only known from the listing it appears
in.

## Pages

| Purpose | URL |
|---------|-----|
| Meeting index of a study group | `/md/T25-SG12/en` (zero padded: `/md/T25-SG05/en`) |
| Document listing of a meeting | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD` |
| Document listing of a study period | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-COL` |
| Detail page of a document | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN-0520` |
| Summary page of a meeting | `/md/T25-SG12-261015/sum/en` |
| Questions under study | `/net4/ITU-T/lists/loqr.aspx?Group=12&Period=18` |
| Structure of a study group | `/net4/ITU-T/lists/sgstructure.aspx?Group=12&Period=18` |
| Home page of a study group | `/en/ITU-T/studygroups/2025-2028/12/Pages/default.aspx` (zero padded: `…/05/…`) |

The `Period` parameter of the `net4` applications is an index of the ITU-T
study periods: `13` is `2005-2008`, `14` is `2009-2012`, `15` is `2013-2016`,
`16` is `2017-2020`, `17` is `2022-2024` and `18` is `2025-2028`.

## Downloads

A document is downloaded from a path that carries the access level of the
document type:

| Type | Path | Access |
|------|------|--------|
| Contribution | `/dms_ties/itu-t/md/{sp}/sg{sg}/c/{id}!!{format}-{lang}.{ext}` | TIES account |
| Temporary document | `/dms_inf/itu-t/md/{sp}/sg{sg}/td/{meeting}/{subtype}/{id}!!{format}-{lang}.{ext}` | TIES account |
| Collective letter | `/dms_pub/itu-t/md/{sp}/sg{sg}/col/{id}!!{format}-{lang}.{ext}` | public |
| Report | `/dms_ties/itu-t/md/{sp}/sg{sg}/r/{id}!!{format}-{lang}.{ext}` | TIES account |

`{sg}` is the zero padded study group, so study group 5 becomes `sg05`.

`{sp}` is the two-digit start year of the study period, `{format}` the format
code (`MSW` for Word, `PDF`, `ZIP`, `HTM`) and `{lang}` the language code
(`E`, `F`, `S`, `A`, `C`, `R`).

## Authentication

The protected documents are behind the F5 BIG-IP access policy at
`auth.itu.int`, which delegates to the SAML identity provider at
`login.itu.int`. A complete login has six steps:

1. **Request a protected document.** The access policy answers with a redirect
   to `auth.itu.int/F5Networks-SSO-Req?SSO_ORIG_URI=…`, which serves a page
   carrying a SAML `AuthnRequest` for the identity provider.
2. **Post the `SAMLRequest`** to `login.itu.int/saml/idp/profile/redirectorpost/sso`.
   The identity provider answers with its logon page.
3. **Post the user name and the password** to `login.itu.int/my.policy`. The
   identity provider answers with a small page that submits itself and carries
   a `dummy` value.
4. **Post that `dummy` value** back to
   `login.itu.int/saml/idp/profile/redirectorpost/sso`. The identity provider
   answers with the page that carries the SAML `Response`.
5. **Post the `SAMLResponse`** to `auth.itu.int/saml/sp/profile/post/acs`, the
   assertion consumer service. It answers with a redirect to
   `www.itu.int/F5Networks-SSO-Resp`, which establishes the session cookie on
   `www.itu.int` and redirects to the requested document.
6. **Fetch the requested document.** The session cookie authorises every
   further request under `/dms_ties` and `/dms_inf`.

Two things are worth knowing:

- The handshake has to start at a **protected** resource. A session that was
  opened for a public page does not authorise the document files.
- The login is finished when the assertion consumer service accepted the
  response. What the requested document answers afterwards — a file, a `404`,
  an error page — does not say anything about the login.

The package implements this chain in `itu_doc_downloader.auth.ties`. The
session cookies live in the HTTP client, so one login serves every following
request.

### Where the credentials come from

`itu_doc_downloader.config.Settings` resolves the TIES credentials from the
highest priority source that provides them. The priority is per setting:

1. the environment variables `ITU_TIES_USERNAME` and `ITU_TIES_PASSWORD`,
2. the `[credentials]` table of `~/.config/itu-doc-downloader/config.toml`,
3. a [secretspec](https://github.com/cachix/secretspec) provider, when the
   optional `secretspec` extra is installed and a `secretspec.toml` declares the
   two secrets under the provider alias `itu-ties`.

The secretspec layer lives in `itu_doc_downloader.config.secretspec_source`. It
contributes the two credentials only as a pair — when either value is missing it
contributes nothing — and it is ignored entirely when the extra is not installed
or the provider cannot be resolved. Installing the package without the extra
therefore behaves exactly as before.

## Page size

The document listings are paginated. The number of documents per page is kept
in the cookie `ITUDMS_PageSize`, which the web interface accepts between 10
and 900. The package sets it to 900, which keeps a whole listing on one page.

## Character set

The meeting document pages are encoded in ISO-8859-1 but do not declare it in
their content type header, while the `net4` applications use UTF-8. The HTTP
client therefore falls back to ISO-8859-1 when the response declares no
charset.
