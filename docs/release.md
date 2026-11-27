---
title: Releasing
---

## The version scheme

The project uses [CalVer](https://calver.org/): `YYYY.MM.N`, for example
`2026.11.1`.

| Component | Meaning                                                                    |
| --------- | -------------------------------------------------------------------------- |
| `YYYY`    | The year of the release. The year is the major component, so the versions sort by release date. |
| `MM`      | The month of the release, two digits, `01` to `12`.                          |
| `N`       | The number of the release within that month. It starts at `1` and counts up; a new month starts at `1` again. |

The alternatives were a plain date (`YYYY.MM.DD`) and a counter per year
(`YYYY.MINOR.PATCH`):

- A plain date forbids a second release on the same day and encodes the day,
  which nobody needs.
- `YYYY.MINOR.PATCH` counts the releases of a year. That number says nothing
  about when a release happened, and a patch release has no version of its
  own.
- `YYYY.MM.N` says when the release happened and how many releases happened in
  that month. The first release of a month is `YYYY.MM.1`.

The version is PEP 440 conformant, so `2026.11.1` is a valid release version
and sorts correctly for `pip`.

### The tag and the published version

The tag of a release is the version without a prefix: `2026.11.1`. A `v` prefix
is accepted as well (`v2026.11.1`), the published version never carries it.
The tag of a push to `main` is created by the workflow, see
[Every push is a release](#every-push-is-a-release).

PEP 440 does not allow a leading zero in the release segment, so the published
version drops the zero of the month: the tag `2027.01.1` publishes the version
`2027.1.1`. The tag keeps the zero, because `2027.01.1` is the spelling a human
reads and `2027.1.1` looks like a date. The build backend drops the zero, so
the name of the artifact, the metadata and the release on PyPI all carry the
same version.

The version is never written into `pyproject.toml`. The build backend
([uv-dynamic-versioning](https://pypi.org/project/uv-dynamic-versioning/))
reads it from the git tag, so the tag is the single source of truth.

### What a build resolves

| State of the repository                        | Resolved version               |
| ---------------------------------------------- | ------------------------------ |
| `HEAD` carries the tag `2026.11.1`            | `2026.11.1`                    |
| `HEAD` carries the tag `2027.01.1`            | `2027.1.1`                     |
| `HEAD` is three commits after the tag         | `2026.11.1.dev3+g1bc24fd`      |
| `HEAD` carries the tag, the tree is dirty      | `2026.11.1.dev0+g1bc24fd.dirty` |
| The repository holds no CalVer tag             | `2026.11.0.dev9+g1bc24fd`      |
| No git at all, for example an exported tarball | `0.0.0.dev0`                   |

Only the first two rows are a release. Every other row is a development
version that a package index must never receive. The counter of a development
version without a tag is `0`, because there is no release to count. Check what
a build resolves with:

```bash
mise version      # or: uvx uv-dynamic-versioning
```

## Every push is a release

Every push to `main` is released. The `version` job of the release workflow
computes the next version, tags the commit and pushes the tag; the rest of
the workflow builds, tests and publishes that version.

The version of a push is the next CalVer version: the counter of the month
counts the releases of that month and starts at `1` in every month. The first
push of November 2026 is released as `2026.11.1`, the second one as
`2026.11.2`, and the first push of December 2026 as `2026.12.1`.

The tag is pushed with the token of the workflow. GitHub does not run a
workflow for a push that its own token made, so the release of the automatic
tag is the run that created it — there is no second run and no double
release.

A commit that carries a tag already is skipped: a tag that was pushed by
hand has its own release. To retry a release that failed, re-run the failed
jobs of the run, not the whole run — the version of a whole run that is
repeated is the next version, not the one that failed.

The version of a push can be computed locally:

```bash
python .github/scripts/calver.py next --tags $(git tag --list)
```

## Cutting a release by hand

A release can also be cut by hand, for example when a version has to be
skipped or the counter has to be set to a certain number.

1. Make sure the `main` branch is green and that you have pulled the
   changes you want to release.
2. Tag the release. The tag is the version, the counter counts the releases
   of the month.
3. Push the tag. The workflow takes over from there.

```bash
git switch main
git pull --rebase
git status --short          # must be empty, a dirty tree is not a release
git tag 2026.11.1
git push origin 2026.11.1
```

Do not bump a version in `pyproject.toml` and do not edit the changelog of the
release — the workflow generates the changelog from the commits between the
previous tag and the new one.

To undo a release that has not been published yet, delete the tag on the
remote (`git push --delete origin 2026.11.1`) and tag again. A version that is
already on PyPI cannot be replaced.

### The local dry run

The same steps run locally, without publishing anything:

```bash
mise release      # check the tag, print the version, build the artifacts
mise version      # print the version the build backend resolves
mise build        # build the sdist and the wheel into dist/
```

## What the release workflow does

`.github/workflows/release.yml` runs on every push to `main` and on every
pushed tag.

| Job             | What it does                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `version`       | Determines the version: the version of a pushed tag, or the next version and the tag of a push to `main`.            |
| `build`         | Builds the sdist and the wheel with `uv build` and checks the names of the artifacts.                              |
| `test`          | Installs the built wheel on CPython 3.13, 3.14 and the free-threaded 3.14t and runs the test suite against it.      |
| `publish`       | Publishes the sdist and the wheel to PyPI with trusted publishing.                                                  |
| `github-release`| Creates the GitHub release with the generated changelog and attaches the artifacts.                                  |

Nothing is published before the wheel has been tested on all three supported
interpreters. The workflow stops at the first failing job.

## The artifacts

The package is pure Python, so the wheel is a single `py3-none-any` wheel:

```text
itu_t_documents-2026.11.1-py3-none-any.whl
itu_t_documents-2026.11.1.tar.gz
```

A `py3-none-any` wheel is valid for every interpreter the project supports,
including the free-threaded 3.14t. Publishing a wheel per interpreter would
only fragment the wheel index without adding anything.

[cibuildwheel](https://cibuildwheel.pypa.io/) is the tool that builds the
free-threaded wheels of a package with compiled code, and it refuses to build
a pure Python wheel at all ("Build failed because a pure Python wheel was
generated"). The moment the project gains a compiled extension, the `build`
job has to switch to `uvx cibuildwheel` and the wheel has to be built per
interpreter. Until then, the universal wheel plus the `test` job of the
workflow is what proves the support for 3.13, 3.14 and 3.14t.

### The free-threaded build

The free-threaded build of CPython uses its own stable ABI, `abi3t`. A wheel
that uses the classic `abi3` ABI is not compatible with it. The runtime
dependencies of the project ship `cp314t` wheels, so they install on 3.14t.

The optional `secretspec` extra and the documentation builder `zensical` only
ship `abi3` wheels, so they cannot be installed on 3.14t. The free-threaded
job of the continuous integration therefore installs the runtime dependencies
and the test tools alone. The extra stays optional, it is inert when it is
not installed.

The free-threaded build enables the GIL by default. The free-threaded job
sets `PYTHON_GIL=0`, so the test suite really runs without the GIL.

## Configuration

### PyPI

The publish step uses [trusted publishing](https://docs.pypi.org/trusted-publishers/):
PyPI verifies the identity of the workflow with the OIDC token of the job, no
API token is involved.

The project does not exist on PyPI yet, so the publisher is a **pending
publisher**. It is created on the account, not on a project, and the first
upload creates the project.

1. Open the **Publishing** page of the PyPI account,
   <https://pypi.org/manage/account/publishing/>, and add a **GitHub
   Actions** publisher.
2. Fill in the pending publisher:
   - **PyPI project name**: `itu-t-documents`
   - **Owner**: `jr2804`
   - **Repository**: `itu-t-documents`
   - **Workflow filename**: `release.yml`
   - **Environment**: leave it empty
3. Save it. The publisher stays *pending* until the first upload; that upload
   creates the project and turns the publisher into a normal one.

The environment of the publisher and the environment of the job that uploads
have to be the same. An empty environment means that the workflow must not
run in one, so the `publish` job of the workflow has no `environment`.

The name is reserved, but a pending publisher does not reserve it: if
somebody else registers `itu-t-documents` before the first upload, the
pending publisher is invalidated and has to be created again.

Once the project exists, its publisher is managed on the project page under
**Publishing**.

### GitHub

- The `Release` workflow has to live in the default branch (`main`). PyPI
  resolves the publisher against the workflow file of the default branch.
- The workflow asks for the `id-token: write` permission in the `publish` job
  and for `contents: write` in the `github-release` job. Both are granted by
  the workflow file, so no repository setting has to be changed.
- The `publish` job runs without a GitHub environment, because the publisher
  on PyPI has none.
- Nothing else has to be configured: the actions, the Python interpreter and
  the tools are all fetched by the workflow itself.

### The token-based fallback

If trusted publishing cannot be used, create an API token on PyPI and store it
as the repository secret `PYPI_API_TOKEN`, then replace the `Publish` step
with:

```yaml
      - name: Publish
        uses: pypa/gh-action-pypi-publish@v1
        with:
          packages-dir: dist/
          password: ${{ secrets.PYPI_API_TOKEN }}
```

A token is a secret. It belongs in the repository settings, never in a file
of the repository, and it must be revoked as soon as it leaks.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and on every pull
request:

- the lint, format, type check, spell check and Markdown checks,
- the test suite with the 100 percent coverage gate on CPython 3.13, 3.14 and
  the free-threaded 3.14t,
- a build of the sdist and the wheel.
