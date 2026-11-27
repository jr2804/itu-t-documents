---
title: Getting started
---

This page takes you from nothing to a working setup: installing the package,
giving it a TIES account and fetching the documents of a meeting.

## What you need

- **Python 3.13 or newer.** The package uses the modern typing syntax and
  the free-threaded build is supported as well.
- **A TIES account** — only if you want to *download* documents. Everything
  else — the meetings, the questions, the structure of a study group, the
  metadata of every document — is public and needs no account.

A TIES account is a membership of the ITU-T. Ask your study group chair or
the ITU-T how to get one; see the
[TIES page of the ITU-T](https://www.itu.int/hub/membership/user-account-ties/).

## Installing

=== "uv"

    ```bash
    uv tool install itu-t-documents
    ```

    The command lands in `~/.local/bin` and is available as
    `itu-t-documents`.

=== "pipx"

    ```bash
    pipx install itu-t-documents
    ```

=== "pip"

    ```bash
    python -m pip install itu-t-documents
    ```

    Install it into a virtual environment — the package needs one.

=== "From a clone"

    ```bash
    git clone https://github.com/jr2804/itu-t-documents.git
    cd itu-t-documents
    mise dev          # installs the tools and syncs the environment
    uv run itu-t-documents --help
    ```

    `mise dev` installs the pinned tools of the project and syncs the Python
    environment. Without `mise`, `uv sync --dev` is enough.

The optional [secretspec](https://github.com/cachix/secretspec) extra, which
reads the credentials from a secret manager, is installed with:

```bash
uv tool install "itu-t-documents[secretspec]"
```

## The TIES credentials

The credentials are looked up in this order — the first source that provides
them wins:

1. the environment variables `ITU_TIES_USERNAME` and `ITU_TIES_PASSWORD`,
2. the `[credentials]` table of `~/.config/itu-t-documents/config.toml`,
3. a secretspec provider, when the optional extra is installed.

```bash
export ITU_TIES_USERNAME="you@example.org"
export ITU_TIES_PASSWORD="secret"
```

Or in the configuration file:

```toml
# ~/.config/itu-t-documents/config.toml
[credentials]
username = "you@example.org"
password = "secret"

[general]
cache_dir = "~/.cache/itu-t-documents"
timeout = 30
```

Check that the account works:

```bash
itu-t-documents auth
```

```text
TIES login succeeded.
```

The login is a four-post SAML handshake against `auth.itu.int` and
`login.itu.int`; a complete download adds the request for the document before
it and the fetch of the file after it. The handshake happens once per session
and the session cookie lives in the HTTP client, so every later request reuses
it. [The reference of the DMS](reference/itu-dms.md#authentication) shows the
whole chain.

### Credentials from secretspec

With the optional extra installed, the credentials can live in a secret
manager instead of a file. Declare the two secrets in a `secretspec.toml`:

```toml
[project]
name = "itu-t-documents"
revision = "1.0"

[providers]
itu-ties = "keyring://"

[profiles.default]
ITU_TIES_USERNAME = { description = "TIES account", providers = ["itu-ties"] }
ITU_TIES_PASSWORD = { description = "TIES password", providers = ["itu-ties"] }
```

secretspec itself looks for a file named `secretspec.toml` in the current
directory and its parents. To keep the manifest elsewhere, put it next to the
configuration file — the package looks there as well:

```text
~/.config/itu-t-documents/secretspec.toml
```

or name it explicitly:

```bash
export ITU_SECRETSPEC_MANIFEST="/srv/secrets/itu-t-documents.toml"
```

The manifest is looked up in that order: `ITU_SECRETSPEC_MANIFEST`, the
`general.secretspec_manifest` key of the configuration file, the
`secretspec.toml` of the configuration directory, and finally the discovery of
secretspec itself.

### The membership of the account

A TIES account is valid for the whole ITU-T, but its membership covers only
the study groups it belongs to. The *metadata* of a document is public; the
*file* is not. A document outside the membership answers `401 Unauthorized`,
and the ITU-T blames invalid credentials for it — which is not what happened:

```text
$ itu-t-documents download --document T25-SG13-C-0001 --format MSW
T25-SG13-C-0001 is not accessible with these credentials; the membership of the TIES account does not cover SG13.
The membership of a TIES account covers only the study groups it belongs to.
```

## Your first steps

List the meetings of a study group:

```bash
itu-t-documents meetings --study-group 12
```

```text
270119  Geneva, 19 January - 27 January 2027
261015  E-Meeting, 15 October 2026
260609  Geneva, 09 June - 17 June 2026
250909  Geneva, 09 September - 18 September 2025
250325  E-Meeting, 25 March 2025
250114  Geneva, 14 January - 23 January 2025
```

Fetch the documents of one of them into the local database:

```bash
itu-t-documents sync --study-group 12 --meeting 260609
```

```text
260609: 276 documents
276 documents stored in /home/you/.cache/itu-t-documents/metadata.db
```

Search what was stored:

```bash
itu-t-documents documents --study-group 12 --question 5
itu-t-documents documents --study-group 12 --source "TU Berlin"
itu-t-documents documents --study-group 12 --type TD --limit 10
```

Download a document:

```bash
itu-t-documents download --document T25-SG12-R-0001 --format MSW
```

```text
/home/you/.cache/itu-t-documents/files/T25-SG12-R-0001/MSW-E.docx (161047 bytes)
```

The formats are `PDF`, `MSW` (Word), `ZIP` and `HTM`, the languages are `E`
(English), `F` (French), `S` (Spanish), `A` (Arabic), `C` (Chinese) and `R`
(Russian). Not every document is published in every rendition:
`T25-SG12-C-0192`, for example, is available as `MSW-E` only. The command
names the rendition it could not find rather than writing an empty file.

## The caches

Everything the package has seen stays on disk, so a second run needs no
network and no account:

<figure markdown="span">
  <img src="assets/figures/caches-light.svg#only-light" alt="The site feeds the HTTP cache, the HTTP cache feeds the metadata store, and a download goes from the site straight into the file cache. The command line, the Python API and the MCP server read the metadata store and the file cache." width="100%">
  <img src="assets/figures/caches-dark.svg#only-dark" alt="The site feeds the HTTP cache, the HTTP cache feeds the metadata store, and a download goes from the site straight into the file cache. The command line, the Python API and the MCP server read the metadata store and the file cache." width="100%">
  <figcaption>Metadata takes the long way through the HTTP cache and the metadata store; a file goes straight into the file cache. All three interfaces read the same two stores.</figcaption>
</figure>

| Path | Content |
|------|---------|
| `~/.cache/itu-t-documents/metadata.db` | The SQLite metadata store |
| `~/.cache/itu-t-documents/http-cache.sqlite` | The raw HTTP responses (hishel) |
| `~/.cache/itu-t-documents/files/` | The downloaded documents |

The cache directory is set with `ITU_CACHE_DIR` or the `general.cache_dir`
key of the configuration file.

The raw HTTP cache follows the rules of RFC 9111: it honours the caching
headers of the ITU-T, so a page is fetched again when the site says it
changed. The metadata store and the file cache never expire — a document that
was downloaded once is served from the disk.

## Troubleshooting

**"No TIES credentials found."**
The credentials are not configured. Set them in the environment or in
`~/.config/itu-t-documents/config.toml`; see above.

**"TIES login failed: …"**
The identity provider rejected the credentials. Check the user name and the
password — the ITU-T locks an account after repeated failed attempts.

**"… is not accessible with these credentials"**
The account is valid but its membership does not cover the study group of the
document. Nothing is wrong with the package.

**"the listing holds 900 of 972 documents"**
The package read every page of a listing and still holds fewer documents than
the listing reports: the ITU-T site changed or a row could not be read. The
package refuses an incomplete listing rather than storing a part of it
silently; see
[The ITU-T Document Management System](reference/itu-dms.md).

**A document is missing from a listing**
The numbers of the documents are not consecutive — a withdrawn document leaves
a hole — and a revision is published as a separate rendition. Neither a
number nor a status code proves that a document exists.

**The page is empty or shows an error**
The ITU-T answers some requests with an empty body and a status of 200. Retry
later, and check the [reference of the DMS](reference/itu-dms.md) if it
persists.

## Where to go next

- [The command line](cli.md) — every command and every option.
- [The Python API](python-api.md) — the same things from Python.
- [The MCP server](mcp.md) — the same things for an AI agent.
- [The catalogue of the ITU-T](catalogue.md) — the study periods, the study
  groups, the working groups and the questions.
