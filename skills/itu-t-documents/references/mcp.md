# The MCP server

```bash
itu-t-documents mcp      # speaks the Model Context Protocol over stdio
```

The server waits on stdio until the client disconnects. In an MCP client it is
registered as a stdio server:

```json
{
  "mcpServers": {
    "itu-t-documents": {
      "command": "itu-t-documents",
      "args": ["mcp"]
    }
  }
}
```

## The tools

| Tool | What it answers | Parameters |
| ---- | --------------- | ---------- |
| `list_periods` | The study periods the ITU-T knows. | — |
| `list_study_groups` | The study groups of a period. | `study_period` |
| `list_structure` | The structure of a study group. | `study_group`, `study_period` |
| `search_structure` | The groups and questions that match a text. | `text`, `study_period` |
| `list_meetings` | The meetings of a study group. | `study_group`, `study_period` |
| `list_questions` | The questions under study. | `study_group`, `study_period` |
| `documents_for_question` | The documents handled in a question. | `question`, `study_group`, `meeting`, `doc_type`, `study_period` |
| `contributions_by_source` | The contributions of one organisation. | `source`, `study_group`, `study_period` |
| `search_documents` | The documents that match the filters. | `study_group`, `doc_type`, `meeting`, `question`, `source`, `study_period`, `limit` |
| `top_sources` | The most prolific sources of the last meetings. | `study_group`, `last_meetings`, `study_period`, `limit` |
| `download_document` | One file on disk. | `document_id`, `file_format`, `language`, `output_path` |

The defaults: `study_group` is 12, `study_period` is the current period for
the catalogue and every stored period for the documents, `doc_type` is every
type, `file_format` is `PDF`, `language` is `E`, `limit` is 50 for
`search_documents` and 10 for `top_sources`, `last_meetings` is 3.

## The questions the tools answer

| Question | Tool |
| -------- | ---- |
| "Show me all temporary documents of Q5/12 at meeting 270119." | `documents_for_question(question=5, study_group=12, meeting="270119", doc_type="TD")` |
| "Which contributions did Company Ltd. make to study group 12?" | `contributions_by_source(source="Company Ltd.", study_group=12)` |
| "Which source submitted the most documents to the last three meetings?" | `top_sources(study_group=12, last_meetings=3)` |
| "Download T25-SG12-C-0192 as Word." | `download_document(document_id="T25-SG12-C-0192", file_format="MSW")` |

## The payloads

A document is a dictionary of JSON compatible values:

```json
{
  "document_id": "T25-SG12-C-0192",
  "type": "C",
  "number": 192,
  "subtype": null,
  "title": "...",
  "sources": ["Company Ltd."],
  "questions": ["Q5/12"],
  "posted": "2026-01-15",
  "revision": null,
  "study_group": 12,
  "study_period": "2025-2028",
  "meeting": "260609",
  "detail_url": "https://www.itu.int/..."
}
```

A source count:

```json
{
  "source": "Company Ltd.",
  "documents": 42,
  "contributions": 30,
  "temporary_documents": 12,
  "meetings": ["270119", "261015", "260609"]
}
```

A study period carries `label`, `code`, `start_year`, `end_year` and `current`.

## What differs from the command line, and why

Every tool is equivalent to a command and to a method of the API — the same
question, the same store, the same public method. Three differences are
deliberate:

- **The tools synchronise.** `documents_for_question`, `contributions_by_source`
  and `search_documents` store the meetings they search before they query the
  store, because an agent has no tool to run `sync`. The command line
  separates the two: `sync` stores, `documents` reads the store.
- **The tools limit.** `search_documents` returns at most 50 documents, to
  protect the context of the agent.
- **`top_sources` has no command.** It is the one tool without a counterpart on
  the command line; the API method behind it is `ItuDocuments.top_sources()`.

`auth`, `mcp`, `default` and `sync` exist on the command line only: they start,
configure or feed the package, they do not ask it a question.

## The errors

A tool does not catch what the API raises: the server reports the failed call
to the client, with the message of the error. `AccessDeniedError` means the
membership of the account does not cover the study group,
`IncompleteListingError` that a listing was truncated,
`UnknownEntityError` that the group or the question does not exist.

## The credentials

The tools that only read the metadata need no credentials. `download_document`
needs a TIES account, unless the file is already in the cache. The credentials
resolve from the environment, from `~/.config/itu-t-documents/config.toml` or
from a secretspec provider — the server reads them like every other
interface.
