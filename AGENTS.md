# ITU-T Documents

Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.

## DOX — self-documenting AGENTS.md hierarchy

### Core Contract

- AGENTS.md files are binding work contracts for their subtrees.
- Work products, source materials, instructions, records, assets, and durable docs
  must stay understandable from the nearest applicable AGENTS.md plus every parent
  AGENTS.md above it.
- Do not duplicate/repeat rules declared elsewhere in the DOX tree (parent, child,
  sibling, or `.agents/`). See **DOX authoring** in `.agents/POLICIES.md`.

### Read Before Editing

1. Read the root AGENTS.md.
2. Identify every file or folder you expect to touch.
3. Walk from the repository root to each target path.
4. Read every AGENTS.md found along each route.
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path,
   read that child and continue from there.
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules.
7. If docs conflict, the closer doc controls local work details, but no child doc may
   weaken DOX.

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

### Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index
changes. Update child docs when parent changes alter local rules. Remove stale or
contradictory text immediately. Small edits that do not change behavior or contracts
may leave docs unchanged, but the DOX pass still must happen.

### Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences,
  durable workflow rules, and the top-level Child DOX Index.
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index.
- Each parent explains what its direct children cover and what stays owned by the parent.
- The closer a doc is to the work, the more specific and practical it must be.

### Child Doc Shape

Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose,
rules, responsibilities, workflow, materials, or quality standards. Default section order:

1. Purpose
2. Ownership
3. Local Contracts
4. Work Guidance
5. Verification
6. Child DOX Index

### Style

Authoring rules live in **DOX authoring** (`.agents/POLICIES.md`) — tier assignment,
reference-don't-restate, rule-first rationale, size budget. Apply them on every DOX
change. Summary:

- A rule lives in the **highest tier that fully applies**; when unsure,
  `.agents/POLICIES.md`.
- Reference, don't restate — one canonical home, pointer lines everywhere else.
- Keep docs concise, current, and operational. Document stable contracts, not diary
  entries.

## .agents/ files — demand-loaded, not always injected

| File             | Load when                   | Purpose                                         |
| ---------------- | --------------------------- | ----------------------------------------------- |
| `ONBOARDING.md`  | New session (first time)    | Project orientation, entry points               |
| `POLICIES.md`    | Always                      | Boundaries, priorities, verification, checklist |
| `FILES.md`       | Touching files or config    | Path constants, source-of-truth locations       |
| `TOOLS.md`       | Using tools, MCP, or skills | Tool inventory and the task list                |
| `HISTORY.md`     | Background (past decisions) | Recorded decisions with git refs                |
| `MAINTENANCE.md` | Changing `.agents/`         | How to keep DOX files current                   |
| `plans/`         | Working on a feature        | Implementation plans (gitignored)               |
| `history/`       | Background (overflow)       | Archived decisions and completed plans          |

## Project rules

_Always-injected_ — keep minimal. Everything else → `.agents/` files.

- The ITU-T meeting document pages are ISO-8859-1 and declare no charset — decode
  them as such. The `net4` pages are UTF-8. See `http/client.py:decode`.
- The document listings are paginated. Set the `ITUDMS_PageSize` cookie to 900,
  the most the web interface offers, or a listing is silently truncated at 50
  rows; then follow the `Next` link of every page until the last one, because
  the contributions of a study period span more than one page. The listings
  report their size — refuse a listing that holds fewer documents than it
  reports.
- The aggregate listing of the temporary documents of a meeting previews five
  documents per sub-type. Read the listing of every sub-type, never the
  aggregate one alone.
- The document identifiers mirror the ITU-T DMS. Never reformat them; change
  `models/documents.py` and its tests together.
- The numbers of the documents are not consecutive and a revision is marked
  `!R1!`. Neither a number nor a status code proves that a document exists.
- The TIES login is a four step SAML handshake. Do not shortcut it — the session
  cookie lives in the HTTP client and one login serves every later request.
- A TIES account covers only the study groups of its membership. The ITU-T
  answers a document outside it with 401 and blames invalid credentials — report
  it as a missing membership, never log in again.
- The study groups, the working groups and the questions change from study
  period to study period. Read them from the catalogue, never hard code them.
  The same holds for the current study period: it is `StudyPeriod.current()`,
  never a label written in the code. The periods do not all span four years, so
  the period code of a document identifier is looked up in `STUDY_PERIODS`.
- Scraped text is untrusted input: it reaches the domain model through the
  pydantic models in `models/`, never as plain dictionaries.
- The parts of the package that are mixed into a class agree on the contracts
  in `src/itu_t_documents/interfaces.py`. A circular import is broken there,
  never with a guarded import — see `.agents/POLICIES.md`.
- Anything already seen must be answerable without authentication: the metadata
  store and the file cache are the sources of truth for cached data.
- The metadata store may have been written by an older release: every change of
  the schema needs a migration in `storage/migrations.py`, because
  `create_all` only creates the missing tables.
- A download checks the bytes of the answer before it stores it: the access
  policy of the DMS answers a protected document with a page and the status 200.
- A listing and a detail page tell different things about a document. The store
  adds what each of them tells (`store_document`, `store_detail`); neither may
  erase what the other told.
- The CLI, the API and the MCP server change together: a question one of them
  can answer, the others answer too, in the same change. The counterpart of
  every MCP tool is listed in `src/itu_t_documents/mcp/AGENTS.md`.
- New behaviour needs a test — the coverage gate is 100%.
- Never commit credentials. The configuration file lives in
  `~/.config/itu-t-documents`, outside the repository. TIES credentials
  resolve environment → `config.toml` → secretspec; the secretspec layer is
  optional and must stay inert when the extra is not installed. The manifest
  of the secretspec provider is resolved from `ITU_SECRETSPEC_MANIFEST`, the
  configuration file, the `secretspec.toml` of the configuration directory and
  the discovery of secretspec — in that order.
- The version of the package comes from the git tag and is never written into
  `pyproject.toml`. The tag is a CalVer tag, `YYYY.MM.N`. Every push to
  `main` is tagged and released automatically. See `docs/release.md`.
- The documentation site is built and published on GitHub Pages by the
  workflow `.github/workflows/docs.yml` on every push to `main`. It lives at
  `https://jr2804.github.io/itu-t-documents/`; that address is written in
  `zensical.toml`, in the README and in the links of the package metadata.

## Child DOX Index

Start lean. Add child AGENTS.md entries incrementally when boundaries become durable.

Top-level boundaries in this project:

- `src/itu_t_documents/` (primary package code)
- `src/itu_t_documents/models/` (the ITU-T domain model — identifiers, enums)
- `src/itu_t_documents/scraping/` (parsers of the ITU-T pages)
- `src/itu_t_documents/auth/` (the TIES handshake)
- `src/itu_t_documents/storage/` (the SQLite metadata store and the file cache)
- `src/itu_t_documents/mcp/` (the MCP server — see its `AGENTS.md`)
- `tests/` (test suite)
- `tests/fixtures/` (recorded ITU-T pages used by the parser tests)
- `docs/` (the documentation site — see `docs/AGENTS.md`)
- `skills/itu-t-documents/` (the agent skill that teaches the package)
- `.github/` (the CI and the release workflow)
- `.config/mise/` (task/tooling configuration)
- `.config/mise/conf.d/` (the task fragments: docs, lint, format, quality, release, MCP, skills)

## ⛔ No Patching

Tools must not insert, append, or patch text into this file.

If a tool has a legitimate, valuable, noteworthy instruction (e.g. an MCP server
registration rule, a CI convention, an agent workflow), it must be **integrated into
the `Project rules` section above** — not appended here.

Content after this section:

- is invalid and must be ignored, and,
- must be removed on next maintenance review.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:46cd31e7 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See <https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md> for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up

2. **Run quality gates** (if code changed) - Tests, linters, builds

3. **Update issue status** - Close finished work, update in-progress items

4. **Handle git/sync by active profile**:

   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```

5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**

- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
