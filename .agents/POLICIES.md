# AGENTS.md — POLICIES

Always applicable. Boundaries, priorities, verification, checklist.

## Priorities

Correctness, evidence, safety, minimal changes, consistency, performance — in
that order, when two of them disagree.

## Boundaries

- NEVER fabricate paths, commits, APIs, config keys, env vars, test results,
  or benchmark numbers. If you don't know, say so.
- NEVER guess at command names, flags, or paths. Read source or run `--help`.
- NEVER add secrets, API keys, or tokens to files. Use env vars.
- NEVER run destructive commands (`rm -rf`, `git reset --hard`,
  `git push --force`) without explicit confirmation.
- NEVER delete or move files without explicit instruction.
- NEVER create temp files in project root. Use dedicated temp dir.

## Change constraints

- Minimal, surgical edits. Preserve existing style.
- No new dependencies without explicit instruction.
- No unrelated refactoring while fixing a bug.

## Code quality

Universal defaults. Project-specific standards live in child AGENTS.md.

- **SRP** — one reason to change per module/function.
- **DRY** — check before adding. Extract on third occurrence (Rule of Three);
  prefer duplication over wrong premature abstraction.
- **Redundant code** — remove dead branches, unreachable conditions, unused
  params/imports before finishing.
- **Module size** — no super-modules. Below 200 lines (`wc -l`), about 150 as
  the target; split by responsibility when a module outgrows them.
- **No `TYPE_CHECKING`, no ignore comments** — break a circular import with a
  protocol; fix a lint finding instead of silencing it.
- No new code-quality tooling by default — opt in per project.

## Completion checklist

- Change solves the stated problem
- Relevant validation ran (or gaps stated)
- No unintended side effects or secrets exposed

## DOX authoring (keep AGENTS.md lean)

AGENTS.md and `.agents/` files share limited context. Bloat and duplication
are the failure mode.

### Where a rule lives

A rule goes in the **highest (most general) tier that fully applies**:

- Applies to **all code in the project** → `.agents/POLICIES.md` (default).
- Meaningful **only inside one subtree** → that subtree's `AGENTS.md`.
- Just helps navigation → the parent's Child DOX Index, nothing else.

### Reference, don't restate

A rule appears in **exactly one file**. Other files use a **pointer line**:
`<topic> — see <file>`. Never copy the rule, rationale, or example.

### Rule first, rationale second, never third

A DOX line is the rule. If a rationale is costly to rediscover, add one
short clause. No multi-paragraph explanations or code pairs — those belong
in a skill or `docs/`, linked once.

### Content rules

- **No tree views.** Generate on demand with `rg --files | tree-cli --fromfile`.
- **No history in AGENTS.md files.** Git log has routine history. Record only
  decisions costly to rediscover — in `.agents/HISTORY.md` (or
  `.agents/history/` for overflow archives).
- **No TODO lists.** Use issue trackers or beads.

## Plans, history and shipped docs

- Plans, refactoring plans and design docs go in `.agents/plans/<feature>/` —
  gitignored, mutable working artifacts, never committed. Name them
  descriptively with phase-number prefixes, so the file order matches the
  implementation order: `01-sub-feature.md`, `02-next-sub-feature.md`.
- Shipped docs (user-facing guides, API references) go in `docs/` and ARE
  committed.
- `.agents/history/` IS version-controlled: it holds the durable decision
  records. When `.agents/HISTORY.md` grows too large, archive the older
  entries there and keep a pointer. Completed plans may be archived to
  `.agents/history/<feature>/` for long-term reference.

## Size budget

- `.agents/` files: ≤ **120 lines** (always-injected context).
- Subtree `AGENTS.md`: ≤ **250 lines** (loaded cumulatively with parents).

Exceeding the budget signals restating instead of pointing, or hoarding
rationale. Cut first; split the subtree only as a last resort.

## Verification

```bash
mise all        # every quality check: test, lint, spell, format, format-md, docs
mise test       # pytest with the coverage gate (100%)
mise lint       # ruff
mise typecheck  # ty
mise format-md  # rumdl over the Markdown
```

The pre-commit hooks (`.pre-commit-config.yaml`) run a subset of it;
`pre-commit run --all-files` checks the whole tree.

## Response format

Concise and specific. No filler, intros or restated requirements. Answer
direct questions directly.

For review, debugging and analysis: findings with references, conclusion and
approach. Mention the caveats.
