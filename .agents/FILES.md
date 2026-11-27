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
| Package source root    | `src/itu_t_documents/`  | `__init__.py`, `__about__.py` (version)         |
| CLI entry points       | `src/itu_t_documents/cli/`            | `app.py` (Cyclopts app), `args.py`, `commands.py` |
| Test suite             | `tests/`                                                        | `test_*.py`, `conftest.py`                      |
| Project metadata       | `pyproject.toml`                                                | `[project]`, `[tool.pytest.ini_options]`        |
| Linter/formatter       | `ruff.toml`                                                     | Ruff rule selection, line length                |
| Type checker           | `ty.toml`                                                       | ty strictness                                   |
| Markdown linter        | `.config/rumdl.toml`                                            | `line-length`, `flavor`, disabled rules         |
| Tool guidance          | `.agents/TOOLS.md`                                              | Tool inventory, MCP servers, skills, mise tasks |
| mise tasks             | `.config/mise/config.toml` + `.config/mise/conf.d/*.toml`       | `[tasks.dev]`, `[tasks.test]`, `[tasks.docs]`, ... |
| Copier answers         | `.copier-answers.yml`                                           | Template version + answers (regenerated)        |
| Pre-commit config      | `.pre-commit-config.yaml`                                       | Hook list                                       |
| MCP server config      | `.config/mise/conf.d/mcp.toml`                                  | `[tasks.add-mcp-servers]`, tool list            |
| Skills install task    | `.config/mise/conf.d/skills.toml`                               | `[tasks.add-skills]`, skill list                |
| Release tasks          | `.config/mise/conf.d/release.toml`                              | `[tasks.version]`, `[tasks.build]`, `[tasks.release]` |
| Documentation build     | `.config/mise/conf.d/docs.toml`                                 | `[tasks.docs]`, the builder and its plugins     |
| The documentation site  | `docs/`                                                         | `index.md`, `getting-started.md`, `cli.md`, `python-api.md`, `mcp.md`, `catalogue.md` |
| The agent skill         | `skills/itu-t-documents/`                                       | `SKILL.md`, `references/` — how to use the package |
| The site navigation     | `zensical.toml`                                                 | `[project] nav`                                 |
| CI and release         | `.github/workflows/`                                            | `ci.yml`, `release.yml`                         |
| Release changelog      | `.github/scripts/release_notes.py`                              | `release_notes.py`                              |
| Release versioning    | `.github/scripts/calver.py`                                    | `next_version`, `published_version`            |
| Domain model           | `src/itu_t_documents/models/`                               | `documents.py`, `questions.py`, `catalogue.py`, `metadata.py`, `study_periods.py`, `enums.py` |
| Page parsers           | `src/itu_t_documents/scraping/`                             | `listing.py`, `listing_rows.py`, `listing_navigation.py`, `meeting_page.py`, `detail.py`, `meetings.py`, `questions.py`, `catalogue.py`, `pages.py` |
| The catalogue          | `src/itu_t_documents/catalogue.py`                          | `ItuCatalogue`; `catalogue_search.py` (`CatalogueEntry`) |
| The errors             | `src/itu_t_documents/errors.py`                             | `ItuError`, `AccessDeniedError`, `ScrapingError`, `UnknownEntityError` |
| TIES handshake         | `src/itu_t_documents/auth/ties.py`                           | `TiesAuthenticator`, `AuthenticationError`     |
| HTTP access            | `src/itu_t_documents/http/client.py`                        | `ItuHttpClient`, `ItuClient`, `decode`          |
| Configuration           | `src/itu_t_documents/config/settings.py`                    | `Settings`, `TomlConfigSource`                  |
| secretspec credentials  | `src/itu_t_documents/config/secretspec_source.py`           | `secretspec_credentials`, `SecretspecConfigSource` |
| Metadata store         | `src/itu_t_documents/storage/`                             | `database.py` (`MetadataStore`), `tables.py`, `queries.py`, `documents.py`, `questions.py`, `files.py` |
| Document file cache    | `src/itu_t_documents/storage/files.py`                      | `FileCache`                                    |
| URL builders           | `src/itu_t_documents/urls.py`                               | `listing_url`, `detail_url`, `questions_url`    |
| High level API         | `src/itu_t_documents/api.py`                                | `ItuDocuments`, `SyncReport`; `api_sync.py`, `api_queries.py` |
| MCP server             | `src/itu_t_documents/mcp/`                                  | `server.py` (`mcp`, the list of the tools), one module per group of tools |
| Recorded ITU-T pages   | `tests/fixtures/`                                               | `*.html`, the input of the parser tests        |
| Cache directory        | `~/.cache/itu-t-documents/`                                 | `metadata.db`, `http-cache.sqlite`, `files/`   |
| Configuration file     | `~/.config/itu-t-documents/config.toml`                     | `[credentials]`, `[general]`                   |
| secretspec manifest    | `~/.config/itu-t-documents/secretspec.toml`                  | `ITU_SECRETSPEC_MANIFEST`, `general.secretspec_manifest` |

## Naming conventions

- **Repository name** (`project_slug`): kebab-case (`my-project`)
- **Python package** (`package_slug`): snake_case (`my_project`)
- **Layout**: `src/itu_t_documents/`
- **Test files**: `test_<module>.py`
- **Template files** (in source template): `filename.ext.jinja` — the `.jinja`
  suffix is stripped on generation
- **Environment variables**: `ITU_TIES_USERNAME`, `ITU_TIES_PASSWORD`,
  `ITU_CACHE_DIR`, `ITU_CONFIG_DIR`, `ITU_TIMEOUT`, `ITU_MAX_CONCURRENCY`,
  `ITU_USER_AGENT`, `ITU_VERIFY_TLS`
