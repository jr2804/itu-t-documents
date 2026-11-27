"""Generate the changelog of a release from the git history.

The script is called by the release workflow. It lists the commits between the
previous tag and the released tag and groups them by the type of a
conventional commit. Commits without a conventional prefix are listed under
"Other changes".

Usage:
    python .github/scripts/release_notes.py --tag 2026.1.0 --version 2026.1.0
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Sequence

CONVENTIONAL = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s+(?P<subject>.+)$")

SECTIONS: tuple[tuple[str, str], ...] = (
    ("feat", "Features"),
    ("fix", "Bug fixes"),
    ("perf", "Performance"),
    ("refactor", "Refactoring"),
    ("docs", "Documentation"),
    ("test", "Tests"),
    ("build", "Build and release"),
    ("ci", "Continuous integration"),
    ("chore", "Chores"),
)

OTHER = "Other changes"


def git(*args: str) -> str:
    """Run a git command and return its output."""
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def previous_tag(tag: str) -> str | None:
    """Return the tag of the previous release, or None for the first release."""
    try:
        return git("describe", "--tags", "--abbrev=0", f"{tag}^") or None
    except subprocess.CalledProcessError:
        return None


def commits(previous: str | None, tag: str) -> list[tuple[str, str]]:
    """Return the commits between the previous tag and the released tag."""
    revision_range = f"{previous}..{tag}" if previous else tag
    output = git("log", "--no-merges", "--pretty=format:%h%x1f%s", revision_range)
    entries = []
    for line in output.splitlines():
        if not line:
            continue
        commit, _, subject = line.partition("\x1f")
        entries.append((commit, subject))
    return entries


def classify(subject: str) -> tuple[str, str]:
    """Return the section key and the rendered entry of a commit subject."""
    match = CONVENTIONAL.match(subject)
    if match is None:
        return "", subject
    scope = match.group("scope")
    prefix = f"{match.group('type')}({scope})" if scope else match.group("type")
    if match.group("breaking"):
        prefix = f"{prefix}!"
    return match.group("type"), f"{prefix}: {match.group('subject')}"


def repository_url() -> str | None:
    """Return the URL of the origin remote, or None if it cannot be determined."""
    try:
        url = git("remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        return None
    if url.startswith("git@"):
        host, _, path = url.partition(":")
        return f"https://{host.removeprefix('git@')}/{path.removesuffix('.git')}"
    if url.startswith("https://"):
        return url.removesuffix(".git")
    return None


def render(tag: str, version: str, previous: str | None, entries: Sequence[tuple[str, str]]) -> str:
    """Render the changelog as markdown."""
    lines = [f"# {version}", ""]

    grouped: dict[str, list[str]] = {}
    for commit, subject in entries:
        key, rendered = classify(subject)
        grouped.setdefault(key, []).append(f"- {rendered} ({commit})")

    for key, heading in SECTIONS:
        items = grouped.pop(key, [])
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(items)
        lines.append("")

    # The commits without a conventional prefix and the commits of a type
    # without a section of their own.
    other = [item for key, items in grouped.items() for item in items]
    if other:
        lines.append(f"## {OTHER}")
        lines.append("")
        lines.extend(other)
        lines.append("")

    if not entries:
        lines.append("No commits since the previous release.")
        lines.append("")

    url = repository_url()
    if url and previous:
        lines.append(f"**Full changelog**: {url}/compare/{previous}...{tag}")
    elif url:
        lines.append(f"**Full changelog**: {url}/commits/{tag}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Print the changelog of a release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="The tag of the release, for example 2026.1.0")
    parser.add_argument("--version", required=True, help="The published version, for example 2026.1.0")
    arguments = parser.parse_args()

    previous = previous_tag(arguments.tag)
    print(render(arguments.tag, arguments.version, previous, commits(previous, arguments.tag)), end="")


if __name__ == "__main__":
    main()
