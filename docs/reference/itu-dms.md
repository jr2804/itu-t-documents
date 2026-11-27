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

Contributions, collective letters and reports are numbered across the whole
study period, so their identifier carries no meeting. The numbers are **not**
consecutive: a withdrawn document leaves a hole, e.g. `T25-SG13-C-0669` does
not exist between `C-0668` and `C-0670`, and the reports of SG13 skip
`R-0005`, `R-0018` and `R-0028`. A number therefore does not imply that a
document exists.

A temporary document belongs to one meeting and therefore embeds its date and a
sub-type. Its number runs per sub-type across the study period and continues
over the meetings, so `T25-SG13-250303-TD-GEN-0082` and
`T25-SG13-250725-TD-GEN-0083` follow each other. The numbers of two
sub-types may collide: `T25-SG13-250303-TD-GEN-0082` and
`T25-SG13-250303-TD-WP3-0082` are two different documents.

The number of a contribution is unique inside a study group, which means the
meeting of a contribution is only known from the listing it appears in.

## Pages

| Purpose | URL |
|---------|-----|
| Meeting index of a study group | `/md/T25-SG12/en` (zero padded: `/md/T25-SG05/en`) |
| Document listing of a meeting | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD` |
| Document listing of a sub-type | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN` |
| Document listing of a study period | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-COL` |
| Detail page of a document | `/md/meetingdoc.asp?lang=en&parent=T25-SG12-261015-TD-GEN-0520` |
| Summary page of a meeting | `/md/T25-SG12-261015/sum/en` |
| Questions under study | `/net4/ITU-T/lists/loqr.aspx?Group=12&Period=18` |
| Structure of a study group | `/net4/ITU-T/lists/sgstructure.aspx?Group=12&Period=18` |
| Index of the study groups of a period | `/en/ITU-T/studygroups/2025-2028/Pages/default.aspx` |
| Home page of a study group | `/en/ITU-T/studygroups/2025-2028/12/Pages/default.aspx` (zero padded: `…/05/…`) |

The `meetingdoc.asp` addresses redirect to the canonical `/md/{parent}/en`.

The `Period` parameter of the `net4` applications is an index of the ITU-T
study periods: `13` is `2005-2008`, `14` is `2009-2012`, `15` is `2013-2016`,
`16` is `2017-2020`, `17` is `2022-2024`, `18` is `2025-2028` and `19` is
`2029-2032`. A period spans four years; the period that was to start in 2021
was renamed to `2022-2024`, because the extra year was used for the session
that had been postponed.

## The structure of the study groups

The study groups, the working groups and the questions under study change from
study period to period, so they cannot be hard coded:

| Period | Study groups |
|--------|--------------|
| 2013-2016 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2017-2020 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2022-2024 | 02, 03, 05, 09, 11, 12, 13, 15, 16, 17, 20 |
| 2025-2028 | 02, 03, 05, 11, 12, 13, 15, 17, 20, 21 |

SG9 and SG16 existed in 2022-2024 and were replaced by SG21 in 2025-2028. The
list of a period is read from its index page, which links to the page of every
study group.

The structure page of a study group lists its groups in rows of an acronym and
a title:

| Code | Kind |
|------|------|
| `PLEN` | the plenary |
| `WP1/12` | a working group |
| `Q5/12` | a question under study |
| `SG12RG-AFR` | a regional group |
| `FG-AINN` | a focus group |
| `IRG-AVQA` | an intersector rapporteur group |
| `QSDG` | a quality study group |
| `JCA-IMT2020/IMT2030` | a joint coordination activity |

A question follows the working group it belongs to, so the page also tells
which working group handles which question. The questions of the plenary come
before the first working group.

### The aggregate listing of the temporary documents

The listing of the temporary documents of a meeting shows only a **preview of
five documents per sub-type**, no matter how large the page size is. The
meeting `T25-SG13-250303` has 549 temporary documents, but its aggregate
listing holds 30 rows — five for each of the six sub-types `GEN`, `PLEN`,
`WP1`, `WP2`, `WP3` and `WP4`. The listing of a single sub-type holds all of
them, and the aggregate page links to it.

The package therefore reads the aggregate listing, collects the sub-types it
offers and reads every sub-type listing. A study group with a single sub-type
is unaffected: its aggregate listing already holds every document.

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

The extension is the one of the published file and is not implied by the
format: a Word document may be a `.docx`, a `.doc` or a `.msw` file, and
`T25-SG13-R-0001` is published as `!!MSW-E.doc` only. The extension of the
download URL is therefore the authoritative one.

### Revisions

A revised document replaces the `!!` separator by `!R1!`, `!R2!` and so on:

```text
/dms_ties/itu-t/md/25/sg02/c/T25-SG02-C-0001!!MSW-E.docx    the original
/dms_ties/itu-t/md/25/sg02/c/T25-SG02-C-0001!R1!MSW-E.docx   the first revision
```

The detail page of a document lists the original and every revision, and a
revision may be published in more languages than the original. The package
prefers the original and falls back to the lowest revision when the original
is gone.

### Existence

A status code does not tell whether a document exists. The access policy
answers with a redirect to the identity provider *before* it validates the
path, so a real and a made up rendition of a protected document look the same.
Only the public prefix (`dms_pub`) validates the path directly. The reliable
way to find out whether a document exists is its listing or its detail page —
a document that does not exist answers with a page of about 7 kB that carries
no identifier.

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

### The membership of the account

A TIES account is valid for the whole ITU-T, but its membership covers only
the study groups it belongs to. The login succeeds either way — the access
policy decides about the resource after the identity provider has answered.

A document outside the membership answers `401 Unauthorized` with a page that
says *"Access is denied due to invalid credentials"*. The credentials are
valid; the membership is not wide enough. The package reports this as an
`AccessDeniedError` and never logs in again.

The metadata of a document is public: the listings, the detail pages and the
structure pages are read without a login, and only the file itself is
protected.

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

### Where the manifest lives

secretspec looks for a file named `secretspec.toml` in the current directory
and its parents. It knows no other location: neither `~/.config/secretspec/`
nor `~/.secretspec.toml` is searched, and
`~/.config/secretspec/config.toml` holds secretspec's own configuration (such
as `[audit] enabled = false`) rather than a manifest.

The package therefore resolves the manifest itself, in this order:

1. `ITU_SECRETSPEC_MANIFEST`,
2. the `general.secretspec_manifest` key of the configuration file,
3. `secretspec.toml` in the configuration directory, when the file exists,
4. the discovery of secretspec itself.

A manifest that cannot be read — a missing file, a directory — yields no
credentials instead of an error, so the other sources keep working.

## Page size

The document listings are paginated. The number of documents per page is kept
in the cookie `ITUDMS_PageSize`, which the web interface accepts between 10
and 900. The package sets it to 900, which keeps a whole listing of a single
sub-type on one page. The cookie is a correctness requirement and not a
tuning knob: without it the listing of the contributions of
`T25-SG05-250603` holds 50 of 396 rows.

The listing pages report their size (`Results: 82`), so the package compares
the reported number with the number of documents it parsed and refuses an
incomplete listing with `IncompleteListingError` instead of storing a part of
it silently.

The aggregate listing of the temporary documents of a meeting is the one
exception — it previews five documents per sub-type whatever the page size is
(see above).

## Character set

The meeting document pages are encoded in ISO-8859-1 but do not declare it in
their content type header, while the `net4` applications use UTF-8. The HTTP
client therefore falls back to ISO-8859-1 when the response declares no
charset.
