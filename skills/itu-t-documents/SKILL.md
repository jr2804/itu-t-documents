---
name: itu-t-documents
description: Use when the task asks about ITU-T documents, TIES, the Document Management System, study periods, study groups, working groups, questions under study, meeting lists, or document identifiers such as T25-SG12-C-0192 — and when a command line, a Python script or an MCP agent has to find, search or download the meeting documents of an ITU-T study group. The package itu-t-documents does that through a CLI, a Python API and an MCP server.
license: MIT
metadata:
  author: Jan.Reimes
  version: "1.0"
---

# ITU-T Documents

`itu-t-documents` reads the meeting documents of the ITU-T study groups from the
ITU-T Document Management System (DMS), keeps them in a local database and
downloads the files on demand. It offers the same capability three times: as a
command line tool, as a Python API and as an MCP server for AI agents.

The three interfaces are one package: a question the MCP server can answer can
be asked on the command line, and the Python API is the method behind both.

## What to reach for

| The task asks for | Reach for |
| ----------------- | --------- |
| The meetings of a study group | `itu-t-documents meetings --study-group 12` |
| The documents of a meeting | `itu-t-documents sync --study-group 12 --meeting 260609`, then `itu-t-documents documents` |
| The contributions of one company | `itu-t-documents documents --type C --source "Company Ltd."` |
| The documents of one question | `itu-t-documents documents --question 5` |
| One file on disk | `itu-t-documents download T25-SG12-C-0192 --format MSW` |
| The structure of a study group | `itu-t-documents structure --study-group 12` |
| A question an agent asks | the MCP server: `itu-t-documents mcp` |

The command line and the MCP server are covered in
[references/cli.md](references/cli.md) and [references/mcp.md](references/mcp.md),
the Python API in [references/api.md](references/api.md). The vocabulary of the
ITU-T — identifiers, study periods, questions, formats, languages — is in
[references/domain.md](references/domain.md), and the errors that a user hits
and what they mean in [references/troubleshooting.md](references/troubleshooting.md).

## Quick start

```bash
pip install itu-t-documents        # or: uvx itu-t-documents ...

itu-t-documents periods             # the study periods the ITU-T knows
itu-t-documents study-groups -p 2025-2028
itu-t-documents meetings -g 12     # the meetings of study group 12
itu-t-documents sync -g 12 -m 260609
itu-t-documents documents -g 12 -q 5
itu-t-documents download T25-SG12-C-0192 --format MSW -o /tmp/doc.docx
```

`--study-group` defaults to 12, `--study-period` to the current period, and the
working directory does not matter: the metadata store and the file cache live in
`~/.cache/itu-t-documents`.

## The three steps of every question

1. **Find the meeting.** `meetings` lists the meetings of a study group with
   their code (`260609`), their place and their dates. The code is what
   `sync` and `documents --meeting` expect.
2. **Store the documents.** `sync` fetches the documents of a meeting into the
   local database. It reads the listing of every sub-type, never the aggregate
   listing alone, and refuses a listing that holds fewer documents than the
   ITU-T reports. Without a `sync`, `documents` answers from the store and may
   know nothing about the meeting.
3. **Ask.** `documents` filters the store by question, source, type and
   meeting. `download` fetches the file itself, which needs TIES credentials
   unless the file is already cached.

## Credentials

The metadata of the DMS is public; the files behind it are protected by the
TIES access control. A download therefore needs an account:

```bash
export ITU_TIES_USERNAME="..."      # or ~/.config/itu-t-documents/config.toml
export ITU_TIES_PASSWORD="..."
itu-t-documents auth                 # checks whether the credentials work
```

A TIES account covers only the study groups of its membership. A document
outside the membership answers with 401 and a page that blames the
credentials — that is a missing membership, not a wrong password. Do not log
in again, report it as a missing membership.

## In an agent (MCP)

```bash
itu-t-documents mcp                  # speaks MCP over stdio
```

The server offers eleven tools: `list_meetings`, `list_questions`,
`documents_for_question`, `contributions_by_source`, `search_documents`,
`top_sources`, `download_document`, `list_periods`, `list_study_groups`,
`list_structure` and `search_structure`. Each tool is equivalent to a command
and to a method of the API — see [references/mcp.md](references/mcp.md) for the
table and for the differences that are deliberate.

## In Python

```python
from itu_t_documents import ItuDocuments, StudyPeriod

with ItuDocuments() as api:
    meeting = api.list_meetings(study_group=12, study_period=StudyPeriod.current())[0]
    api.sync_meeting(study_group=12, study_period=StudyPeriod.current(), meeting=meeting)
    for record in api.find_documents(study_group=12, question=5):
        print(record.document_id, record.title)
```

## Rules that save time

- The document identifier is the address of a document: `T25-SG12-C-0192`
  (period `T25`, study group `12`, type `C`, number `0192`). Never reformat it.
- The number of the documents is not consecutive and a revision is marked
  `!R1!`. A number does not prove that a document exists.
- A document is published in the format it was submitted in. `T25-SG12-C-0192`
  exists as MSW only — asking for a PDF of it fails.
- The study groups, the working groups and the questions change from study
  period to study period. Read them from the catalogue, never hard code them.
- Everything already seen is answerable without a login: the metadata store and
  the file cache are the sources of truth for cached data.
