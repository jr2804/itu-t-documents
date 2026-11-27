# ITU-T Documents — MCP Server

The MCP server of the package. `itu-t-documents mcp` speaks the Model Context Protocol over stdio and offers the capability of the package to an AI agent as eleven tools.

## Purpose

This folder is the whole MCP server: the server instance, its instructions, the tools and what the tools share. An agent uses it to answer questions such as "show me all TDs of Q5/12 at meeting XYZ", "which contributions were made by company XYZ in study group 12?" and "which source submitted the most documents to the last three meetings?".

## Ownership

- Owned here: every file in this folder — the tools with their names, parameters, docstrings and payloads, and the instructions of the server.
- Not owned here: the API the tools call (`src/itu_t_documents/api.py`, `src/itu_t_documents/catalogue.py`), the CLI (`src/itu_t_documents/cli/`), the metadata store and the caches. When a tool needs something they do not offer, they are changed first and the tool calls the change.
- The user guide of the tools is `docs/mcp.md`; it follows `docs/AGENTS.md`.

## Local Contracts

### Parity with the CLI and the API

**An MCP tool is always equivalent to the CLI and the API: it answers the same question, from the same store, through the same public method of the API.**

The three interfaces are one package. Whoever can ask the MCP server something can ask the command line the same, and whoever reads the Python API finds the method behind both. A capability that exists in one interface only is a gap in the other two, not a feature of the one.

| Tool | API method | CLI command |
| -------------- | ------------------------------- | ------------------------------ |
| `list_meetings` | `ItuDocuments.list_meetings()` | `meetings` |
| `list_questions` | `ItuDocuments.list_questions()` | `questions` |
| `documents_for_question` | `ItuDocuments.documents_for_question()` | `documents --question` |
| `contributions_by_source` | `ItuDocuments.contributions_by_source()` | `documents --source` with `--type C` |
| `search_documents` | `ItuDocuments.find_documents()` | `documents` |
| `top_sources` | `ItuDocuments.top_sources()` | — no command yet |
| `download_document` | `ItuDocuments.download()` | `download` |
| `list_periods` | `StudyPeriod.all()` | `periods` |
| `list_study_groups` | `ItuCatalogue.study_groups()` | `study-groups` |
| `list_structure` | `ItuCatalogue.structure()` | `structure` |
| `search_structure` | `ItuCatalogue.search()` | `search` |

The table is binding. `tests/test_mcp_server.py` reads it and fails when a tool has no row, when the API method of a row does not exist or when the CLI command of a row is not registered.

The differences below are deliberate. Any other difference between a tool and its counterparts is a defect:

- **Synchronising.** `documents_for_question`, `contributions_by_source` and `search_documents` synchronise the meetings they search before they query the store, because an agent has no tool to run `sync` itself. The command line separates the two: `sync` stores, `documents` reads the store.
- **Limits.** `search_documents` returns at most 50 documents by default, to protect the context of the agent. `documents` returns every match until `--limit` says otherwise.
- **`top_sources`** counts the `last_meetings` most recent meetings, where the API method takes their codes. It is the one tool without a command: `WITHOUT_COMMAND` in `tests/test_mcp_server.py` lists it, and that list only shrinks.
- **`download_document`** takes `document_id`, `file_format`, `language` and `output_path`. The options of the command are `--document`, `--format`, `--language` and `--output-file`.
- **Errors.** A tool does not catch what the API raises: the server reports a failed call to the client. The command line reports an error its own way.
- **Commands without a tool.** `auth`, `mcp`, `default` and `sync` exist on the command line only. They start, configure or feed the package; they do not ask it a question.

### The tool contract

- The name of a tool, its parameters with their types and defaults, its docstring and the keys of its payload are its public interface: a client reads them from the tool list and an agent decides by them. Renaming or removing one breaks every installed client, so it is changed together with `docs/mcp.md` and the MCP table of `README.md`.
- The docstring of a tool is the description the agent reads. Its first line says what the tool returns. A tool that exists for one of the questions in [Purpose](#purpose) says so in "Use this to answer …". `Args` gives an example for every parameter that is not a plain number.
- A parameter that stands for an enumeration arrives as a string, such as `"TD"`, `"MSW"` or `"E"`. It is converted at the edge with the enumeration of the package, `DocType(...)` or `DocFormat(...)`. A parameter is never widened to spare the conversion.
- A tool holds no state. A call that needs the study period resolves it with `resolve_period()` before it opens the package with `open_api()`, which closes it when the call ends, even when the call fails.
- A payload is a dictionary of JSON compatible values: a date is an ISO string, an enumeration is its value, what is unknown is `None`. `payloads.py` builds the payload of a document and of a source count; a tool builds the rest where it returns it.
- `INSTRUCTIONS` in `server.py` is what the client shows as the instructions of the server: what the server does and what it needs.

## Work Guidance

- **Layout.** One module per group of questions: `meetings.py`, `documents.py`, `sources.py`, `download.py` and `catalogue.py`, each holding only its tools. `server.py` puts the server together: it owns the server, its instructions and the complete list of the tools. What the tools share lives in `support.py` and `payloads.py`.
- **Adding a tool.** The API has a public method for the question and the command line a command for it. Then, in this order: the tool in the module of its question, its line in `server.py`, its row in the table above, a test of its behaviour in `tests/test_mcp.py`, its entries in `docs/mcp.md` and in the MCP table of `README.md`.
- **Changing a tool.** Its API method, its command, its row, its tests and its documentation change in the same change as the tool.
- **The other direction.** A change of the command line or of the API reaches this folder in the same change. The rule is a project rule of the root `AGENTS.md`.
- **Size.** The module size rule is in `.agents/POLICIES.md` (Code quality). A module of tools that outgrows it is split by the question it answers, never by layer.
- **Imports.** Nothing outside this folder imports it. The MCP libraries take longer to load than the rest of the command line together, so the `mcp` command loads the package by name when it runs; `tests/test_mcp_server.py` pins this. Inside the folder, imports stand at the top of the module.

## Verification

```bash
mise run test                  # tests/test_mcp.py and tests/test_mcp_server.py are part of the suite
mise run lint
mise run typecheck
uv run itu-t-documents mcp     # the server starts and waits on stdio; stop it with Ctrl-C
```

A tool is done when its code, its row in the table, its test in `tests/test_mcp.py` and `docs/mcp.md` agree.

## Child DOX Index

This folder has no children. The project rules are in the root `AGENTS.md`, the decisions in `.agents/HISTORY.md` and the paths in `.agents/FILES.md`.
