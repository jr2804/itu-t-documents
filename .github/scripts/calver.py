"""Compute the CalVer versions of the releases.

The scheme is YYYY.MM.N: the year, the month, and the number of the release
within that month. The counter starts at 1 in every month, so the first
release of November 2026 is "2026.11.1" and the second one is "2026.11.2".

PEP 440 does not allow a leading zero in the release segment, so the
published version drops the zero of the month: the tag "2027.01.1" publishes
the version "2027.1.1". The tag keeps the zero, because that is the spelling
a human reads.

Usage:
    python .github/scripts/calver.py next --tags 2026.10.3 2026.11.1
    python .github/scripts/calver.py publish 2026.11.1
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime

VERSION = re.compile(r"^v?(?P<year>\d{4})\.(?P<month>0[1-9]|1[0-2])\.(?P<counter>[1-9]\d*)$")


def parse_version(version: str) -> tuple[int, int, int] | None:
    """Return the year, the month and the counter of a CalVer tag.

    A tag that is not a CalVer tag yields None, the tag may carry a "v"
    prefix.
    """
    match = VERSION.match(version)
    if match is None:
        return None
    return int(match["year"]), int(match["month"]), int(match["counter"])


def published_version(version: str) -> str:
    """Return the version as PEP 440 writes it, without the zero of the month."""
    parts = parse_version(version)
    if parts is None:
        raise ValueError(f"'{version}' is not a CalVer version")
    year, month, counter = parts
    return f"{year}.{month}.{counter}"


def next_version(tags: Iterable[str], year: int, month: int) -> str:
    """Return the version of the release that follows the given tags.

    The counter counts the releases of the month, so it starts at 1 in every
    month. The version is the greatest one of the repository: a release of a
    later month that exists already is counted further, so that the version
    never goes back.
    """
    versions = [parsed for tag in tags if (parsed := parse_version(tag)) is not None]
    same_month = [counter for tag_year, tag_month, counter in versions if tag_year == year and tag_month == month]
    counter = max(same_month, default=0) + 1
    if versions and (year, month, counter) < max(versions):
        year, month, counter = max(versions)
        counter += 1
    return f"{year:04d}.{month:02d}.{counter}"


def main() -> None:
    """Print the version of the next release or the published form of a tag."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    following = commands.add_parser("next", help="the version of the next release")
    following.add_argument("--tags", nargs="*", default=[], help="the tags of the repository")
    following.add_argument("--date", default=None, help="the date of the release, YYYY-MM-DD (default: today, UTC)")
    publishing = commands.add_parser("publish", help="the published version of a tag")
    publishing.add_argument("version")
    arguments = parser.parse_args()

    if arguments.command == "next":
        day = date.fromisoformat(arguments.date) if arguments.date else datetime.now(UTC).date()
        print(next_version(arguments.tags, day.year, day.month))
    else:
        print(published_version(arguments.version))


if __name__ == "__main__":
    main()
