---
title: Overview
hide:
- feedback
---

The documents of ITU-T study group meetings are published in the ITU-T
Document Management System (DMS). Most of them are protected by the TIES
access control and need an account.

`itu-t-documents` reads the metadata of every document type — contributions
(`C`), temporary documents (`TD`), collective letters (`COL`) and reports
(`R`) — keeps it in a local database, and downloads the documents on demand.
It is a Python library, a command line tool and an MCP server for AI agents.

## Three interfaces

| Interface | For |
|-----------|-----|
| [The command line](cli.md) | working in a shell, scripting a study group |
| [The Python API](python-api.md) | embedding the package in your own tool |
| [The MCP server](mcp.md) | letting an AI agent answer the questions of a user |

All three read the same local caches, so a document that was downloaded once
is available to all of them without another login.

## A first look

```bash
# The meetings of study group 12
itu-t-documents meetings --study-group 12

# The documents of one of them, into the local database
itu-t-documents sync --study-group 12 --meeting 260609

# What was handled in question 5
itu-t-documents documents --study-group 12 --question 5

# The document itself
itu-t-documents download --document T25-SG12-C-0192 --format MSW
```

The metadata is public; only the download needs a
[TIES account](getting-started.md#the-ties-credentials) — or a copy of the
file that is already in the cache.

## What it knows

- **Every document type** with its number, title, sources, questions and
  posting date.
- **The structure of the ITU-T** — the study periods, the study groups of a
  period, the working groups, the questions under study and their
  rapporteurs. The structure changes from period to period, so it is read
  from the ITU-T and never hard coded; see
  [the catalogue](catalogue.md).
- **The access level of every document.** Contributions and reports are
  TIES documents, temporary documents are internal to a study group, and
  collective letters sit on a public path. A download still needs a TIES
  account unless the file is already in the cache, because the package
  authenticates before it asks the DMS for the file.

## The caches

Everything the package has seen stays on disk, so a second run needs no
network and no account. The metadata store, the HTTP cache and the downloaded
files live in `~/.cache/itu-t-documents`; [Getting started](getting-started.md#the-caches)
lists the files and shows how they fit together.

## The documentation

### Guide

- [Getting started](getting-started.md) — install the package, give it a TIES
  account, fetch the documents of a meeting, and what to do when something
  goes wrong.
- [The command line](cli.md) — every command and every option of
  `itu-t-documents`.
- [The Python API](python-api.md) — the same things from Python: the API, the
  models, the catalogue, the metadata store, the file cache and the errors.
- [The MCP server](mcp.md) — the tools for an AI agent and the questions they
  answer.
- [The catalogue of the ITU-T](catalogue.md) — the study periods, the study
  groups, the working groups and the questions under study.

### Reference

- [API reference](reference/api.md) — the generated reference of every public
  class and function.
- [The ITU-T Document Management System](reference/itu-dms.md) — the URL
  layout, the numbering scheme and the authentication chain of the ITU-T, as
  they were reverse engineered from the live pages.

### Development

- [Contributing](contributing.md) — how to set the project up and what the
  quality gates are.
- [Releasing](release.md) — the version scheme and how a release is cut.

### About

- [Credits](credits.md) — the people and the projects this package stands on.
- [Code of Conduct](code_of_conduct.md)
- [License](license.md)
