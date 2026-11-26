# ITU-T Document Downloader

> Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="#"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776ab?logo=python"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"></a>
</p>
<!-- markdownlint-enable MD033 -->

---

## Quick Start

```bash
# Install dependencies
mise dev
```

## Usage

### Running Tests

```bash
mise test
# or
uv run pytest
```

### Code Quality

```bash
mise lint       # ruff + ty + codespell
mise format     # ruff format + isort
mise all        # test + lint + format in one pass
mise bump       # bump pyproject bounds, then uv sync -U for all groups/extras
```

### CLI Commands

```bash
uv run itu-doc-downloader                  # default command
uv run itu-doc-downloader greet Alice      # greet someone
uv run itu-doc-downloader add 5 3          # add numbers
uv run itu-doc-downloader greet Alice -o out.txt --no-cache
uv run itu-doc-downloader --version        # show version
```

| Environment Variable | Description |
|----------------------|-------------|
| `ITU_DOC_DOWNLOADER_CACHE` | Enable/disable caching (true/false) |
| `ITU_DOC_DOWNLOADER_OUTPUT_FILE` | Default output file path |

Install shell completion (after the command is available on your `PATH`):

```bash
itu-doc-downloader --install-completion
```

## Development

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

### Documentation

```bash
mise docs-serve          # live preview at http://localhost:8000
mise docs-build          # build static site to site/
```

## AI Dev-Features

This project includes optional AI-agent tooling. After `mise dev`, install with:

```bash
mise run add-mcp-servers <agent>   # register MCP servers (claude, codex, gemini, ...)
mise run add-skills                # install agent skills
```

Enabled dev-features are listed in `.config/mise/conf.d/mcp.toml` and
`.config/mise/conf.d/skills.toml`.

<!--
Documentation upgrade prompt for coding agents:

When this project is stable / contains a sufficient amount of code, upgrade the
documentation as follows:

1. Improve this README.md (the project's start page) by applying the skills
   good-readme and beautify-github-readme, and (if applicable) visual-explainer,
   effective-html, and mermaid-diagrams.
2. Organize extended documentation under docs/ — apply the project-docs skill
   first to structure the docs tree.
3. Enrich technically complex code with useful figures by applying the skills
   mermaid-diagrams, visual-explainer, effective-html, and scientific-figures.
-->

## Project Structure

```text
itu-doc-downloader/
├── .config/mise/               # mise task definitions
├── docs/                       # MkDocs documentation
├── src/itu_doc_downloader/     # Source package
│   ├── __init__.py
│   ├── __about__.py
│   └── cli/
│       ├── __init__.py
│       ├── app.py
│       ├── args.py
│       └── commands.py
├── tests/                      # Test suite
├── .copier-answers.yml         # Template version tracking
├── pyproject.toml              # uv + hatch + pytest config
├── ruff.toml                   # Linter + formatter config
├── ty.toml                     # Type checker config
├── TOOLS.md                    # Tool usage notes
└── README.md
```

## Tech Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Package manager | [uv](https://docs.astral.sh/uv/) | Fast installs, deterministic lockfile |
| Task runner | [mise](https://mise.jdx.dev/) | DAG-based tasks, tool version management |
| Linter + formatter | [ruff](https://docs.astral.sh/ruff/) | Single-binary code quality |
| Type checker | [ty](https://github.com/google/ty) | Strict type checking |
| Testing | [pytest](https://pytest.org/) | Test framework with 100% coverage gate |
| CLI | [Cyclopts](https://cyclopts.readthedocs.io/) | Type-driven CLI parsing and shell completion |
| Spell check | [codespell](https://github.com/codespell-project/codespell) | Code and doc spell checking |
| Documentation | [Zensical](https://github.com/zensical/zensical) | MkDocs Material with executable examples |
| Versioning | [uv-dynamic-versioning](https://github.com/ninoseki/uv-dynamic-versioning) | Git tag-based versioning |
| Hooks | [pre-commit](https://pre-commit.com/) | Automated quality gate |

## License

MIT — see [LICENSE](LICENSE) for details.

---

Generated from [copier-uv-plus](https://codeberg.org/jr2804/copier-uv-plus).
