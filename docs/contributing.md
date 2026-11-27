---
title: Contributing
---

## Contributing

Contributions are welcome! Here's how you can help.

### Development Setup

```bash
# Clone the repository (replace <repo-url> with your fork)
git clone <repo-url>.git
cd itu-doc-downloader

# Install the pinned tool versions (ruff, ty, rumdl, pyreorder, ...).
# Node.js and Bun are expected on PATH; add them to mise.local.toml or run
# `mise use -g node` / `mise use -g bun` if you want mise to manage them.
# then sync the dev dependencies declared in pyproject.toml.
# (mise install is the mise command that installs the tool versions in
# .config/mise/config.toml; it is NOT a task — `mise dev` is the task that
# syncs Python dev deps.)
mise install
uv sync --dev
# or: mise dev    # composite task that runs `uv sync -U --dev --all-extras --all-groups`
```

### Running Tests

```bash
mise test          # pytest with coverage
```

### Code Quality

```bash
# The single command a contributor should run before opening a PR:
mise all           # runs test, lint, spell, format, format-md, docs

# Individual steps (use these while iterating):
mise lint          # ruff check --fix
mise spell         # codespell
mise typecheck     # static type check (ty)
mise format        # ruff format + ruff check --select I + pyreorder run
mise format-md     # rumdl over Markdown
mise bump          # uv-bump, then uv sync -U --dev --all-extras --all-groups
mise docs          # build the Zensical documentation
```

### The documentation builder

The documentation builder is a tool, not a dependency of the package, so it
runs outside the project environment. `mise docs` calls `uvx` with the
builder and the plugins it needs and pins the interpreter:

```bash
mise docs
# uvx --python 3.13 --with zensical==0.1.3 --with 'mkdocstrings[python]>=0.29' \
#   --with 'markdown-exec>=1.8' --with 'markdown-callouts>=0.4' zensical build
```

The builder does not import the package — mkdocstrings reads the source
statically — so the runtime dependencies are not needed to build the
documentation. The versions of the builder and its plugins live in
`.config/mise/conf.d/docs.toml`, next to the other tools of the project.

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
