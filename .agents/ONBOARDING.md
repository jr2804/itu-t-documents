# AGENTS.md — ONBOARDING

Read this when starting a new session. After first read, only revisit when
project structure or tooling changes significantly.

## Project

Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP. Full docs at `README.md` or `docs/`.

## Quick start

```bash
mise dev        # install dependencies (uv sync --dev)
mise test       # run pytest with coverage
mise lint       # ruff + ty + codespell
mise format     # ruff format + isort + pyreorder
mise all        # test + lint + format in one pass
```

## Entry points (read these first)

| File / Section | Why |
| -------------- | --- |
| `AGENTS.md` | Root rail — rules + `.agents/` index |
| `.agents/POLICIES.md` | Boundaries, priorities, verification |
| `.agents/FILES.md` | Source-of-truth locations for this package |
| `.agents/TOOLS.md` | Installed CLIs, MCP servers, skills, and mise tasks |
| `pyproject.toml` | Dependencies, pytest config, build backend |
| `.copier-answers.yml` | Template answers (regenerated on `copier update`) |

## Layout

- **`src/itu_doc_downloader/`** — primary package source (src layout)
- **`src/itu_doc_downloader/models/`** — the ITU-T domain model (identifiers, enums, questions)
- **`src/itu_doc_downloader/scraping/`** — parsers of the ITU-T pages
- **`src/itu_doc_downloader/auth/`** — the TIES handshake
- **`src/itu_doc_downloader/storage/`** — the SQLite metadata store and the file cache
- **`src/itu_doc_downloader/cli/`** — Cyclopts CLI
- **`src/itu_doc_downloader/mcp_server.py`** — the FastMCP server
- **`tests/`** — pytest suite (100% coverage gate), `tests/fixtures/` holds the recorded pages
- **`docs/`** — Zensical / MkDocs Material documentation
- **`.config/mise/`** — task runner config (`config.toml` + `conf.d/` fragments)

## The ITU-T at a glance

- Documents live in the ITU-T DMS on `www.itu.int`; most of them need a TIES account.
- A document is `T{period}-SG{group}[-{meeting}]-{type}[-{subtype}]-{number}`.
- The metadata pages are public, the document files are not.
- The reverse engineered scheme is written up in `docs/reference/itu-dms.md`.

## Where to dig deeper

- `docs/` — user-facing documentation
- `.agents/HISTORY.md` — past decisions and rationale
- Source-tree AGENTS.md files — local contracts for each area

## Available tools

The inventory of CLIs, MCP servers, skills, and tasks lives in
`.agents/TOOLS.md`. The optional MCP dev-features and the skill set are not
installed by default — `mise run add-mcp-servers <agent>` and `mise run
add-skills` install what `.config/mise/data/dev-features.csv` and
`.config/mise/data/skills.csv` enable.
