---
title: The MCP server
---

The package is an MCP server, so an AI agent can answer the questions of an
ITU-T user with the data of the ITU-T at hand.

```bash
itu-t-documents mcp
```

The server speaks the Model Context Protocol over stdio. It opens no port and
keeps no state between calls: every tool opens the package, answers from the
caches or the ITU-T, and closes it again.

## Registering the server

Add it to the configuration of your agent. For Claude Code:

```bash
claude mcp add itu-t-documents -- itu-t-documents mcp
```

For any other client, the entry is the same — the command that starts the
server and the environment it inherits:

```json
{
  "mcpServers": {
    "itu-t-documents": {
      "command": "itu-t-documents",
      "args": ["mcp"],
      "env": {
        "ITU_TIES_USERNAME": "you@example.org",
        "ITU_TIES_PASSWORD": "secret"
      }
    }
  }
}
```

The credentials of the environment are inherited from the agent, so an agent
that runs in your shell finds them on its own.

## The tools

| Tool | Parameters | Answers |
|------|------------|---------|
| `list_meetings` | `study_group`, `study_period` | *"When does SG12 meet?"* |
| `list_questions` | `study_group`, `study_period` | *"Which questions are under study?"* |
| `documents_for_question` | `question`*, `study_group`, `meeting`, `doc_type`, `study_period` | *"Show me all TDs of Q5/12 at meeting XYZ"* |
| `contributions_by_source` | `source`*, `study_group`, `study_period` | *"Which contributions were made by company XYZ in study group 12?"* |
| `top_sources` | `study_group`, `last_meetings`, `study_period`, `limit` | *"Which source submitted the most documents (TD + C) to the last three meetings?"* |
| `search_documents` | `study_group`, `doc_type`, `meeting`, `question`, `source`, `study_period`, `limit` | *"Show me the contributions of Huawei in SG12"* |
| `download_document` | `document_id`*, `file_format`, `language`, `output_path` | *"Download T25-SG12-R-0001 as Word"* |
| `list_periods` | — | *"Which study periods are there?"* |
| `list_study_groups` | `study_period` | *"Which study groups does the ITU-T have?"* |
| `list_structure` | `study_group`, `study_period` | *"Which working groups does SG13 have?"* |
| `search_structure` | `text`*, `study_period` | *"Which working group deals with speech?"* |

A parameter marked with an asterisk is required. Every tool that takes them
defaults to study group `12` and the current study period; `search_documents`
returns at most 50 documents, and `top_sources` looks at the last 3 stored
meetings and returns 10 sources.

The search tools read the metadata store. They synchronise only what the store
lacks: `documents_for_question`, `contributions_by_source` and
`search_documents` sync the study group when it has no stored document, and a
named meeting when that meeting has none. A question about data that is
already stored never touches the network. `top_sources` also reads the store;
when the study group has no documents, it synchronises the group first, then
counts its last three stored meetings. The `meeting` parameter has the store
limitation described in [the CLI guide](cli.md#documents).

`list_questions` separates the people by role: `rapporteurs`,
`co_rapporteurs` and `other_people`.

## The three questions the tools exist for

### *"Show me all TDs of Q5/12 at meeting XYZ"*

```json
{
  "question": 5,
  "study_group": 12,
  "meeting": "261015",
  "doc_type": "TD"
}
```

The tool synchronises the named meeting when the store has none of its
documents, then queries the database. A meeting that is already stored is
answered offline.

### *"Which contributions were made by company XYZ in study group 12?"*

```json
{
  "source": "TU Berlin",
  "study_group": 12
}
```

The match is partial and case insensitive, so `TU Berlin` also finds
`Technische Universität Berlin (TU Berlin)`. The first call on an empty store
synchronises the study group, so it can take a while; later calls answer from
the store.

### *"Which source submitted the most documents (TD + C) to the last three meetings?"*

```json
{
  "study_group": 13,
  "last_meetings": 3
}
```

The tool counts the last three stored meetings of the study group — after
synchronising the group when the store is empty — and answers with the most
prolific sources.

## The catalogue tools

The last four tools answer the questions about the *structure* of the ITU-T:
which study periods there are, which study groups a period has, which working
groups and questions a study group has, and which of them deal with a topic.

```json
{
  "text": "speech",
  "study_period": "2025-2028"
}
```

They need no account — the structure of the ITU-T is public. See
[the catalogue](catalogue.md).

## What the agent cannot do

The server runs with the rights of the user who started it. An agent can
download every document the account may see — and nothing more: a document
outside the membership of the account answers `401 Unauthorized`, and the
server reports that as a missing membership.

The tools never write to the ITU-T. The package only reads the web site and
writes to the local cache.

## The caches

The server uses the same caches as the command line, in
`~/.cache/itu-t-documents`. An agent that asks the same question twice
answers the second time from the local cache when the data is stored; a
question about data the store lacks synchronises it first.
