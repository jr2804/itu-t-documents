# ITU-T Documents

> Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="#"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776ab?logo=python"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"></a>
</p>
<!-- markdownlint-enable MD033 -->

<img src="assets/icon.svg" width="64" height="64" align="right">

The documents of ITU-T study group meetings are published in the ITU-T Document
Management System (DMS). Most of them are protected by the TIES access control
and need an account. This package scrapes the metadata, keeps it in a local
database and downloads the documents on demand.

---

## Features

- **Metadata of every document type** — contributions (`C`), temporary
  documents (`TD`), collective letters (`COL`) and reports (`R`), with their
  number, title, sources, questions and posting date.
- **Study group structure** — the questions under study with their working
  group (`WP1/12`, `PLEN`, …) and their rapporteurs.
- **TIES authentication** — the SAML handshake against `auth.itu.int` and
  `login.itu.int` is performed automatically.
- **Local caches** — the raw HTTP responses are cached with
  [hishel](https://hishel.com/), the metadata in a SQLite database and the
  downloaded documents on disk. Cached data never needs authentication again.
- **Complete listings** — a listing is read per sub-type and compared with the
  number of documents the ITU-T reports, so a truncated listing is never
  stored as if it were complete.
- **Three interfaces** — a Python API, a command line interface and an MCP
  server for AI agents.

## Quick Start

```bash
# Install the dependencies
mise dev

# List the meetings of study group 12
uv run itu-t-documents meetings --study-group 12

# Fetch the documents of a meeting into the local database
uv run itu-t-documents sync --study-group 12 --meeting 260609

# Search them
uv run itu-t-documents documents --study-group 12 --question 5
```

## TIES credentials

Downloading a document needs a [TIES](https://www.itu.int/hub/membership/user-account-ties/)
account. The credentials are read from the environment:

```bash
export ITU_TIES_USERNAME="you@example.org"
export ITU_TIES_PASSWORD="secret"
```

or from `~/.config/itu-t-documents/config.toml`:

```toml
[credentials]
username = "you@example.org"
password = "secret"

[general]
cache_dir = "~/.cache/itu-t-documents"
timeout = 30
```

Both are optional; the environment wins over the file. A third, lowest priority
source is a [secretspec](https://github.com/cachix/secretspec) provider — see
[Credentials from secretspec](#credentials-from-secretspec).

### The membership of the account

A TIES account is valid for the whole ITU-T, but its membership covers only
the study groups it belongs to. The metadata of a document — its listing, its
title, its sources — is public and is read without a login, but the file
itself is not: a document outside the membership answers `401 Unauthorized`
with a page that blames invalid credentials, which is not what happened. The
package reports that as a missing membership:

```text
$ itu-t-documents download --document T25-SG13-C-0001 --format MSW
T25-SG13-C-0001 is not accessible with these credentials; the membership of
the TIES account does not cover SG13.
```

Check that the login works with:

```bash
uv run itu-t-documents auth
```

### Credentials from secretspec

[secretspec](https://github.com/cachix/secretspec) keeps secrets in a provider
(keyring, 1Password, Vault, a dotenv file, …) and declares them in a
`secretspec.toml`. Install the optional extra and declare the two TIES secrets
under the provider alias `itu-ties`:

```bash
uv sync --extra secretspec
```

```toml
# secretspec.toml
[project]
name = "itu-t-documents"
revision = "1.0"

[providers]
itu-ties = "keyring://"

[profiles.default]
ITU_TIES_USERNAME = { description = "TIES account", providers = ["itu-ties"] }
ITU_TIES_PASSWORD = { description = "TIES password", providers = ["itu-ties"] }
```

Store the values once, then run the downloader from the directory that holds the
manifest:

```bash
secretspec set ITU_TIES_USERNAME
secretspec set ITU_TIES_PASSWORD
uv run itu-t-documents auth
```

secretspec itself only ever looks for a file named `secretspec.toml` in the
current directory and its parents. To keep the manifest somewhere else, put it
next to the configuration file — the package looks there as well:

```text
~/.config/itu-t-documents/secretspec.toml
```

or name it explicitly:

```bash
export ITU_SECRETSPEC_MANIFEST="/srv/secrets/itu-t-documents.toml"
```

The manifest is looked up in this order: `ITU_SECRETSPEC_MANIFEST`, the
`general.secretspec_manifest` key of the configuration file, the
`secretspec.toml` of the configuration directory, and finally the discovery of
secretspec itself.

secretspec is consulted only when neither `ITU_TIES_USERNAME`/`ITU_TIES_PASSWORD`
nor the configuration file provide the credentials. Without the extra, or without
a matching provider, it is ignored silently.

## The ITU-T numbering scheme

Every document is addressed by study period, study group, document type and an
increasing number. Temporary documents carry the meeting and a sub-type:

| Type | Identifier | Example |
|------|------------|---------|
| Contribution | `T{sp}-SG{sg}-C-{number}` | `T25-SG12-C-0192` |
| Temporary document | `T{sp}-SG{sg}-{meeting}-TD-{subtype}-{number}` | `T25-SG12-261015-TD-GEN-0520` |
| Collective letter | `T{sp}-SG{sg}-COL-{number}` | `T25-SG12-COL-0001` |
| Report | `T{sp}-SG{sg}-R-{number}` | `T25-SG12-R-0001` |

`T25` is the study period `2025-2028`, `SG12` the study group, `261015` the
meeting (15 October 2026) and `0520` the number of the document. Contributions,
collective letters and reports are numbered across the whole study period, so
their identifier carries no meeting. The numbers are not consecutive — a
withdrawn document leaves a hole — and the number of a temporary document runs
per sub-type over the whole study period.

## The catalogue of the ITU-T

The study groups, the working groups and the questions change from study
period to period — SG9 and SG16 existed in 2022-2024 and were replaced by SG21
in 2025-2028. They are therefore read from the ITU-T and never hard coded, and
an entity that does not exist is refused instead of being returned empty.

```python
from itu_t_documents import ItuCatalogue, StudyPeriod

with ItuCatalogue() as catalogue:
    period = StudyPeriod.from_year(2025)          # the period that starts in 2025

    [group.code for group in catalogue.study_groups(period)]   # SG02, SG03, SG05, …

    structure = catalogue.structure(12, period)
    structure.question(5).title                   # the title of Q5/12
    structure.question(99)                        # raises UnknownEntityError
```

## Python API

```python
from itu_t_documents import DocType, ItuDocuments, StudyPeriod

with ItuDocuments() as api:
    period = StudyPeriod.from_year(2025)

    # Fetch the documents of a meeting and store them locally
    api.sync_meeting(12, meeting, period, (DocType.CONTRIBUTION, DocType.TEMPORARY_DOCUMENT))

    # All temporary documents of Q5/12
    for document in api.documents_for_question(study_group=12, question=5, doc_type=DocType.TEMPORARY_DOCUMENT):
        print(document.document_id, document.title)

    # The most prolific sources of the last three meetings
    for source in api.top_sources(study_group=12, meetings=("270119", "261015", "260609")):
        print(source.count, source.source)
```

## CLI

```text
itu-t-documents auth                          # check the TIES credentials
itu-t-documents periods                       # list the study periods
itu-t-documents study-groups                  # list the study groups of a period
itu-t-documents structure --study-group 12    # the groups and questions of a study group
itu-t-documents search --search speech        # search the groups of the ITU-T
itu-t-documents meetings                      # list the meetings of a study group
itu-t-documents questions                     # list the questions under study
itu-t-documents sync --meeting 260609         # fetch and store the documents
itu-t-documents documents --question 5        # search the stored documents
itu-t-documents documents --source "TU Berlin"
itu-t-documents download --document T25-SG12-C-0192 --format PDF
itu-t-documents mcp                           # run the MCP server over stdio
```

| Option | Description |
|--------|-------------|
| `--study-group`, `-g` | Study group number, e.g. `12` |
| `--study-period`, `-p` | Study period, e.g. `2025-2028` |
| `--meeting`, `-m` | Meeting code as used by the ITU-T, e.g. `270119` |
| `--type` | Document type: `TD`, `C`, `COL` or `R` |
| `--question`, `-q` | Restrict to a question number |
| `--source`, `-s` | Restrict to a submitting organisation |
| `--format` | Download format: `PDF`, `MSW` (Word), `ZIP` or `HTM` |
| `--language` | Language code: `E`, `F`, `S`, `A`, `C` or `R` |

## MCP server

```bash
uv run itu-t-documents mcp
```

The server offers the tools `list_meetings`, `list_questions`,
`documents_for_question`, `contributions_by_source`, `top_sources`,
`search_documents` and `download_document`. They answer the questions that
ITU-T users ask most often:

- *"Show me all TDs of Q5/12 at meeting XYZ"* — `documents_for_question`
- *"Which contributions were made by company XYZ in study group 12?"* —
  `contributions_by_source`
- *"Which source submitted the most documents (TD + C) to the last three
  meetings?"* — `top_sources`

The catalogue of the ITU-T is offered as well: `list_periods`,
`list_study_groups`, `list_structure` and `search_structure` answer *"Which
study groups are there?"* and *"Which working group deals with speech?"*.

## Caches

| Path | Content |
|------|---------|
| `~/.cache/itu-t-documents/metadata.db` | The SQLite metadata store |
| `~/.cache/itu-t-documents/http-cache.sqlite` | The raw HTTP cache (hishel) |
| `~/.cache/itu-t-documents/files/` | The downloaded documents |

## Development

```bash
mise test        # pytest with the 100% coverage gate
mise lint        # ruff + ty + codespell
mise format      # ruff format + isort
mise docs        # build the documentation
mise all         # test + lint + format in one pass
```

The documentation builder is a tool, not a dependency of the package: `mise
docs` runs it through `uvx` with a pinned interpreter, outside the project
environment.

The version of the package is a CalVer version — `YYYY.MINOR.PATCH`, e.g.
`2026.1.0` — and it is derived from the git tag, never written into
`pyproject.toml`. Pushing a tag builds the artifacts, tests them on CPython
3.13, 3.14 and the free-threaded 3.14t, publishes them to PyPI and creates the
GitHub release. The procedure is documented in
[docs/release.md](docs/release.md).

The reverse engineered URL and numbering scheme is documented in
[docs/reference/itu-dms.md](docs/reference/itu-dms.md).

## Tech Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Package manager | [uv](https://docs.astral.sh/uv/) | Fast installs, deterministic lockfile |
| Task runner | [mise](https://mise.jdx.dev/) | DAG-based tasks, tool version management |
| Linter + formatter | [ruff](https://docs.astral.sh/ruff/) | Single-binary code quality |
| Type checker | [ty](https://github.com/google/ty) | Strict type checking |
| Testing | [pytest](https://pytest.org/) | Test framework with 100% coverage gate |
| CLI | [Cyclopts](https://cyclopts.readthedocs.io/) | Type-driven CLI parsing and shell completion |
| HTTP | [httpx](https://www.python-httpx.org/) | HTTP client with the TIES session |
| HTTP cache | [hishel](https://hishel.com/) | RFC 9111 compliant response cache |
| Database | [SQLModel](https://sqlmodel.tiangolo.com/) | Typed SQLite metadata store |
| Settings | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Layered configuration |
| Parsing | [lxml](https://lxml.de/) | HTML parser for the ITU-T pages |
| MCP | [FastMCP](https://gofastmcp.com/) | Model Context Protocol server |
| Spell check | [codespell](https://github.com/codespell-project/codespell) | Code and doc spell checking |
| Documentation | [Zensical](https://github.com/zensical/zensical) | MkDocs Material with executable examples |
| Versioning | [uv-dynamic-versioning](https://github.com/ninoseki/uv-dynamic-versioning) | Git tag-based versioning |
| Hooks | [pre-commit](https://pre-commit.com/) | Automated quality gate |

## License

MIT — see [LICENSE](LICENSE) for details.

---

Generated from [copier-uv-plus](https://codeberg.org/jr2804/copier-uv-plus).
