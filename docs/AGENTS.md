# ITU-T Documents — Documentation

The documentation site of the package, built with
[zensical](https://github.com/jr2804/zensical). This file is the contract for
everything in `docs/`.

## Purpose

The site answers three questions for three audiences:

- a user who wants to install the package and get the documents of a meeting —
  [Getting started](getting-started.md),
- a user who wants to drive the package — [The command line](cli.md),
  [The Python API](python-api.md), [The MCP server](mcp.md),
- a user who wants to know what the ITU-T publishes and how the package
  reads it — [The catalogue of the ITU-T](catalogue.md) and
  [The ITU-T Document Management System](reference/itu-dms.md).

The API reference is generated from the docstrings; every other page is
written by hand.

## Ownership

- `index.md` — the landing page of the site.
- `getting-started.md`, `cli.md`, `python-api.md`, `mcp.md`, `catalogue.md` —
  the guide.
- `reference/api.md` — the generated reference. Never edit it by hand.
- `reference/itu-dms.md` — the write-up of the reverse engineered ITU-T web
  site. It is a record of measurements, not a description of wishes.
- `release.md`, `contributing.md` — the development pages.
- `credits.md`, `license.md`, `code_of_conduct.md` — the boilerplate pages.
- `assets/figures/` — the sources (`.mmd`, `.py`) and the rendered
  `-light.svg` / `-dark.svg` pairs of the figures.
- `assets/stylesheets/docs.css` — the small stylesheet for figures and
  captions; it is registered in `zensical.toml`.
- The navigation lives in `zensical.toml`, not in the pages.

## Local Contracts

- Every page starts with a front matter block that carries its title.
- The guide pages link to each other by their file name, so the links work in
  the repository and in the built site.
- The pages describe what the package does. A command that is not there is
  not documented; a behaviour that is not implemented is not promised.
  Verify against `--help`, the docstrings and the code before writing it.
- The examples show real output. Take the output from a real run, never from
  memory.
- The name of the project is `itu-t-documents`, the command is
  `itu-t-documents` and the Python package is `itu_t_documents`. The
  distribution on PyPI is `itu-t-documents`, the repository is
  `github.com/jr2804/itu-t-documents`.
- The caches live in `~/.cache/itu-t-documents`, the configuration in
  `~/.config/itu-t-documents`, and the environment variables are prefixed
  with `ITU_`.

## Work Guidance

- The README is the landing page of the repository. The site has its own
  landing page in `index.md`; the README is not included, because its links
  are relative to the repository and would break in the site.
- A new page goes into the navigation of `zensical.toml` in the same change.
- A change of the package that the guide describes — a new command, a new
  setting, a new error — is documented in the same change.
- Do not repeat what another page says. Link to it.
- A figure is generated from its source in `assets/figures/`, never edited in
  the SVG. Mermaid sources render with
  `.agents/skills/mermaid-diagrams/scripts/render.mjs`; the catalogue figure
  and the quantitative figures are Python scripts with explicit coordinates
  and the scientific-figures conventions. Embed the light
  and dark pair with `#only-light` and `#only-dark` inside
  `<figure markdown="span">`, and give every image an alt text and the figure
  a caption that states its claim.
- The reference of the DMS is the record of what the ITU-T actually answers.
  When a measurement contradicts it, the measurement wins and the page is
  corrected.

## Verification

```bash
mise docs          # build the site
mise format-md     # lint the Markdown
```

The build is strict about broken links and missing pages: `zensical build
--strict` turns every warning into an error. Run it before opening a pull
request, and check the built site under `site/` for the pages you touched.

## Child DOX Index

This folder has no children. The rules of the repository live in the root
`AGENTS.md`, the decisions in `.agents/HISTORY.md` and the paths in
`.agents/FILES.md`.
