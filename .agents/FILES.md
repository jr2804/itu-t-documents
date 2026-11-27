# AGENTS.md — FILES

Single source of truth for paths, config keys, and naming conventions.
Kept compact — agents hallucinate less when they know where definitions live.

## Pattern

- One file owns each class of definition (paths, config defaults, enums).
- Import from that file. Never hard-code values in other modules.
- Variables that address files get `_file` suffix; directories get `_dir`.

## Project-specific sources of truth

| What                   | Where                                                           | Key names                                       |
| ---------------------- | --------------------------------------------------------------- | ----------------------------------------------- |
| Package source root    | `src/itu_doc_downloader/`  | `__init__.py`, `__about__.py` (version)         |
| CLI entry points       | `src/itu_doc_downloader/cli/`            | `app.py` (Cyclopts app), `args.py`, `commands.py` |
| Test suite             | `tests/`                                                        | `test_*.py`, `conftest.py`                      |
| Project metadata       | `pyproject.toml`                                                | `[project]`, `[tool.pytest.ini_options]`        |
| Linter/formatter       | `ruff.toml`                                                     | Ruff rule selection, line length                |
| Type checker           | `ty.toml`                                                       | ty strictness                                   |
| Markdown linter        | `.config/rumdl.toml`                                            | `line-length`, `flavor`, disabled rules         |
| Tool guidance          | `TOOLS.md`                                                      | Preferred diff tool for supported files         |
| mise tasks             | `.config/mise/config.toml` + `.config/mise/conf.d/*.toml`       | `[tasks.dev]`, `[tasks.test]`, ...              |
| Copier answers         | `.copier-answers.yml`                                           | Template version + answers (regenerated)        |
| Pre-commit config      | `.pre-commit-config.yaml`                                       | Hook list                                       |
| MCP server config      | `.config/mise/conf.d/mcp.toml`                                  | `[tasks.add-mcp-servers]`, tool list            |
| Skills install task    | `.config/mise/conf.d/skills.toml`                               | `[tasks.add-skills]`, skill list                |
| Release tasks          | `.config/mise/conf.d/release.toml`                              | `[tasks.version]`, `[tasks.build]`, `[tasks.release]` |
| CI and release         | `.github/workflows/`                                            | `ci.yml`, `release.yml`                         |
| Release changelog      | `.github/scripts/release_notes.py`                              | `release_notes.py`                              |
| Domain model           | `src/itu_doc_downloader/models/`                               | `documents.py`, `questions.py`, `catalogue.py`, `enums.py` |
| Page parsers           | `src/itu_doc_downloader/scraping/`                             | `listing.py`, `detail.py`, `meetings.py`, `questions.py`, `catalogue.py` |
| The catalogue          | `src/itu_doc_downloader/catalogue.py`                          | `ItuCatalogue`, `CatalogueEntry`               |
| The errors             | `src/itu_doc_downloader/errors.py`                             | `ItuError`, `AccessDeniedError`, `UnknownEntityError` |
| TIES handshake         | `src/itu_doc_downloader/auth/ties.py`                           | `TiesAuthenticator`, `AuthenticationError`     |
| HTTP access            | `src/itu_doc_downloader/http/client.py`                        | `ItuHttpClient`, `ItuClient`, `decode`          |
| Configuration           | `src/itu_doc_downloader/config/settings.py`                    | `Settings`, `TomlConfigSource`                  |
| secretspec credentials  | `src/itu_doc_downloader/config/secretspec_source.py`           | `secretspec_credentials`, `SecretspecConfigSource` |
| Metadata store         | `src/itu_doc_downloader/storage/database.py`                   | `MetadataStore`, the SQLModel tables            |
| Document file cache    | `src/itu_doc_downloader/storage/files.py`                      | `FileCache`                                    |
| URL builders           | `src/itu_doc_downloader/urls.py`                               | `listing_url`, `detail_url`, `questions_url`    |
| High level API         | `src/itu_doc_downloader/api.py`                                | `ItuDocuments`, `DocumentRecord`, `SourceCount` |
| MCP server             | `src/itu_doc_downloader/mcp_server.py`                         | `mcp`, the tool functions                       |
| Recorded ITU-T pages   | `tests/fixtures/`                                               | `*.html`, the input of the parser tests        |
| Cache directory        | `~/.cache/itu-doc-downloader/`                                 | `metadata.db`, `http-cache.sqlite`, `files/`   |
| Configuration file     | `~/.config/itu-doc-downloader/config.toml`                     | `[credentials]`, `[general]`                   |
| secretspec manifest    | `~/.config/itu-doc-downloader/secretspec.toml`                  | `ITU_SECRETSPEC_MANIFEST`, `general.secretspec_manifest` |

## Naming conventions

- **Repository name** (`project_slug`): kebab-case (`my-project`)
- **Python package** (`package_slug`): snake_case (`my_project`)
- **Layout**: `src/itu_doc_downloader/`
- **Test files**: `test_<module>.py`
- **Template files** (in source template): `filename.ext.jinja` — the `.jinja`
  suffix is stripped on generation
- **Environment variables**: `ITU_TIES_USERNAME`, `ITU_TIES_PASSWORD`,
  `ITU_CACHE_DIR`, `ITU_CONFIG_DIR`, `ITU_TIMEOUT`, `ITU_MAX_CONCURRENCY`,
  `ITU_USER_AGENT`, `ITU_VERIFY_TLS`
