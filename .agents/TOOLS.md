# State file — TOOLS

Inventory of development-time tools — CLIs, MCP servers, skills, and project
tasks. Describes current usage, not history. Read it when reaching for a tool;
keep it current (see `.agents/MAINTENANCE.md`).

## Rules

- Use an existing tool before adding a new one. No new tools, MCP servers,
  skills, or dependencies without explicit instruction (`.agents/POLICIES.md`).
- Each tool appears exactly once, in its primary table.
- Tables describe current usage — delete rows when tools leave; this is not a
  historical log.
- Tools are declared in `.config/mise/config.toml`; machine-specific pins live in
  the gitignored `mise.local.toml`. Run `mise up` after pulling, and use
  `mise x -- <tool>` when a tool is not on `PATH`.

## CLI tools & runtimes

| Tool         | When                        | Purpose                                                          |
| ------------ | --------------------------- | ---------------------------------------------------------------- |
| `mise`       | Every session               | Declares the toolchain and runs the project tasks                |
| `uv` / `uvx` | Dependencies, runs, builds  | Syncs the venv, runs tests, builds the wheel                     |
| `ruff`       | Any Python change           | Linter and formatter, configured by `ruff.toml`                  |
| `ty`         | Any Python change           | Type checker, configured by `ty.toml`                            |
| `pyreorder`  | Sorting a module            | Structural reordering of imports, constants, classes, functions |
| `codespell`  | Docs or source prose        | Spell check; part of `mise run all`                              |
| `rumdl`      | Markdown changes            | Lint and format GFM, configured by `.config/rumdl.toml`          |
| `ripgrep`    | Searching the tree          | Fast content search; `rg --files` feeds the tree view            |
| `tree-cli`   | Inspecting layout           | Directory tree of the repository                                 |
| `omnidiff`   | Comparing supported files   | Structured diff instead of a plain text diff — see below         |
| `uv-bump`    | Dependency maintenance      | Bumps dependency bounds; `mise run bump` wraps it                |
| `gh`         | GitHub hosting              | Workflow, release, and pull request status                       |
| `git`        | Every change                | Version control                                                  |
| `beads`      | Multi-session work          | Issue tracker over Dolt — `bd ready`, `bd show`, `bd update`     |
| `dolt`       | Beads storage only          | The database behind `bd`; used embedded, never invoked directly  |
| `zensical`   | Documentation changes       | Builds `docs/` through `mise run docs`                           |

### OmniDiff

Prefer `omnidiff` for any comparison between supported files — source code,
images, fonts, PDFs, archives — instead of a plain text diff.

```shell
omnidiff before.py after.py              # interactive comparison
omnidiff --headless before.png after.png # plain text output for scripts/CI
```

`omnidiff --help` lists every mode; `omnidiff git configure` wires it in as
Git's difftool.

### Beads

The issue tracker keeps its issues in a local Dolt database (`.beads/`) and
syncs them to the upstream repository: the data travels in the reference
`refs/dolt/data` of the same git remote, so a clone carries the issues with
it.

```shell
bd ready                       # the work that can be picked up
bd sync                        # pull, check for conflicts, push
bd bootstrap                   # hydrate a fresh clone from the remote
bd dolt remote list            # the Dolt remote the sync uses
```

The `beads` MCP server runs `mise x --command beads-mcp`, and the tool has to
be resolvable **outside** the project directory as well: an editor or a
harness may start the server from anywhere, and `mise x` then falls back to
the global configuration. `mise use -g pipx:beads-mcp@1.3.4` sets it, and `bd`
and `dolt` are global for the same reason.

## MCP servers

Declared in the gitignored `.mcp.json` by `mise run add-mcp-servers <agent>`,
driven by `.config/mise/data/dev-features.csv`.

| Server  | When                          | Purpose                                                   |
| ------- | ----------------------------- | --------------------------------------------------------- |
| `beads` | Tracking or looking up issues | `beads-mcp` exposes the issue tracker; run via `mise x`   |

## Skills

Installed into `.agents/skills/` by `mise run add-skills`; sources are pinned in
the gitignored `skills-lock.json`.

| Skill        | When                              | Purpose                                                    |
| ------------ | --------------------------------- | ---------------------------------------------------------- |
| `beads`      | Any multi-session tracked work    | Issue workflow, dependencies, recovery after compaction    |
| `beads-docs` | Editing the beads documentation   | Concept model, terminology, and prose conventions          |

## Project scripts & tasks

Task definitions live in `.config/mise/config.toml` and `.config/mise/conf.d/`.

| Command                       | Purpose                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| `mise run dev`                | Sync all dependency groups and extras                            |
| `mise run bump`               | Bump bounds with `uv-bump`, then sync                            |
| `mise run all`                | Aggregate non-mutating gate: test, lint, spell, format, docs     |
| `mise run test`               | `pytest` with the 100% coverage gate                             |
| `mise run lint`               | Apply Ruff fixes, including unsafe ones                          |
| `mise run typecheck`          | `ty check src/ tests/`                                           |
| `mise run spell`              | `codespell src/ tests/`                                          |
| `mise run format`             | Reorder, format, and sort imports                                |
| `mise run format-md`          | Reformat Markdown with `rumdl`                                   |
| `mise run docs`               | Build the documentation site                                     |
| `mise run version`            | Print the version resolved from the git tag                      |
| `mise run build`              | Build the sdist and wheel into `dist/`                           |
| `mise run release`            | Dry run: verify the CalVer tag, then build                       |
| `mise run add-mcp-servers`    | Install dev-feature tools and register their MCP servers         |
| `mise run add-skills`         | Install the optional skill set                                   |
| `mise run clean`              | Remove build artifacts                                           |
| `pre-commit run --all-files`  | Run the hooks in `.pre-commit-config.yaml`                       |

`scripts/gen_credits.py` is embedded into `docs/credits.md` by Zensical rather
than run directly.
