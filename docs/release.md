---
title: Releasing
---

## The version scheme

The project uses [CalVer](https://calver.org/): `YYYY.MINOR.PATCH`, for example `2026.1.0`.

| Component | Meaning                                                                    |
| --------- | -------------------------------------------------------------------------- |
| `YYYY`    | The year of the release. The year is the major component, so the versions sort by release date. |
| `MINOR`   | The number of the release within that year. The first release of a year is `YYYY.1.0`. |
| `PATCH`   | A fix that does not warrant a new minor release. It stays `0` for a regular release. |

The alternatives were a plain date (`YYYY.MM.DD`) and `YY.MM.MICRO`:

- A plain date forbids a second release on the same day and encodes the month
  and the day, which the year already orders.
- `YY.MM.MICRO` is ambiguous across centuries and needs a micro counter that
  has no meaning for a project of this size.
- `YYYY.MINOR.PATCH` says when the release happened and how many releases
  happened that year. The year is the only component a user has to remember.

The version is PEP 440 conformant, so `2026.1.0` is a valid release version
and sorts correctly for `pip`.

### The tag and the published version

The tag of a release is the version without a prefix: `2026.1.0`. A `v` prefix
is accepted as well (`v2026.1.0`), the published version never carries it.

The version is never written into `pyproject.toml`. The build backend
([uv-dynamic-versioning](https://pypi.org/project/uv-dynamic-versioning/))
reads it from the git tag, so the tag is the single source of truth.

### What a build resolves

| State of the repository                        | Resolved version               |
| ---------------------------------------------- | ------------------------------ |
| `HEAD` carries the tag `2026.1.0`             | `2026.1.0`                     |
| `HEAD` is three commits after the tag         | `2026.1.0.dev3+g1bc24fd`       |
| `HEAD` carries the tag, the tree is dirty      | `2026.1.0.dev0+g1bc24fd.dirty` |
| The repository holds no CalVer tag             | `2026.0.0.dev9+g1bc24fd`       |
| No git at all, for example an exported tarball | `0.0.0.dev0`                   |

Only the first row is a release. Every other row is a development version that
a package index must never receive. Check what a build resolves with:

```bash
mise version      # or: uvx uv-dynamic-versioning
```

## Cutting a release

1. Make sure the `main` branch is green and that you have pulled the
   changes you want to release.
2. Tag the release. The tag is the version, the minor component counts the
   releases of the year.
3. Push the tag. The workflow takes over from there.

```bash
git switch main
git pull --rebase
git status --short          # must be empty, a dirty tree is not a release
git tag 2026.1.0
git push origin 2026.1.0
```

Do not bump a version in `pyproject.toml` and do not edit the changelog of the
release — the workflow generates the changelog from the commits between the
previous tag and the new one.

To undo a release that has not been published yet, delete the tag on the
remote (`git push --delete origin 2026.1.0`) and tag again. A version that is
already on PyPI cannot be replaced.

### The local dry run

The same steps run locally, without publishing anything:

```bash
mise release      # check the tag, print the version, build the artifacts
mise version      # print the version the build backend resolves
mise build        # build the sdist and the wheel into dist/
```

## What the release workflow does

`.github/workflows/release.yml` runs when a tag is pushed.

| Job             | What it does                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `verify`        | Rejects a tag that is not a CalVer tag and checks that the build backend resolves the version of the tag.          |
| `build`         | Builds the sdist and the wheel with `uv build` and checks the names of the artifacts.                              |
| `test`          | Installs the built wheel on CPython 3.13, 3.14 and the free-threaded 3.14t and runs the test suite against it.      |
| `publish`       | Publishes the sdist and the wheel to PyPI with trusted publishing.                                                  |
| `github-release`| Creates the GitHub release with the generated changelog and attaches the artifacts.                                  |

Nothing is published before the wheel has been tested on all three supported
interpreters. The workflow stops at the first failing job.

## The artifacts

The package is pure Python, so the wheel is a single `py3-none-any` wheel:

```text
itu_t_documents-2026.1.0-py3-none-any.whl
itu_t_documents-2026.1.0.tar.gz
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

1. Create the project on [PyPI](https://pypi.org/manage/account/publishing/).
   The name `itu-t-documents` is reserved — create the project with it.
2. Open the project, go to **Publishing** and add a **GitHub** publisher.
3. Fill in the publisher:
   - **Owner**: `jr2804`
   - **Repository name**: `itu-t-documents`
   - **Workflow name**: `release.yml`
   - **Environment**: leave it empty. Fill it in only if you add an
     environment to the workflow and want the publisher to be bound to it.
4. Save the publisher. The first publication can take a few minutes, PyPI
   propagates the new publisher before it accepts the upload.

### GitHub

- The `Release` workflow has to live in the default branch (`main`). PyPI
  resolves the publisher against the workflow file of the default branch.
- The workflow asks for the `id-token: write` permission in the `publish` job
  and for `contents: write` in the `github-release` job. Both are granted by
  the workflow file, so no repository setting has to be changed.
- The `test` job of the release workflow and the `test` job of the continuous
  integration need no setting either.

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
