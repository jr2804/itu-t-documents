"""Tests for the CalVer script of the release workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_FILE = Path(__file__).parents[1] / ".github" / "scripts" / "calver.py"

pytestmark = pytest.mark.skipif(
    not SCRIPT_FILE.exists(),
    reason="the scripts of the release workflow are not part of the distribution",
)


def test_parse_version(calver: ModuleType) -> None:
    """A CalVer tag is a year, a month and a counter."""
    assert calver.parse_version("2026.11.1") == (2026, 11, 1)
    assert calver.parse_version("v2026.11.1") == (2026, 11, 1)
    assert calver.parse_version("2027.01.12") == (2027, 1, 12)


@pytest.mark.parametrize("tag", ["2026.13.1", "2026.11.0", "2026.1.1", "1.0.0", "release", ""])
def test_parse_version_rejects_other_tags(calver: ModuleType, tag: str) -> None:
    """A tag that is not a CalVer tag has no version."""
    assert calver.parse_version(tag) is None


def test_published_version_drops_the_zero_of_the_month(calver: ModuleType) -> None:
    """PEP 440 does not allow a leading zero in the release segment."""
    assert calver.published_version("2027.01.1") == "2027.1.1"
    assert calver.published_version("2026.11.1") == "2026.11.1"


def test_published_version_rejects_other_versions(calver: ModuleType) -> None:
    """A version that is not a CalVer version cannot be published."""
    with pytest.raises(ValueError):
        calver.published_version("2026.13.1")


def test_next_version_starts_at_one(calver: ModuleType) -> None:
    """The first release of a month is the version with the counter one."""
    assert calver.next_version([], 2026, 11) == "2026.11.1"


def test_next_version_counts_the_releases_of_the_month(calver: ModuleType) -> None:
    """The counter counts the releases of the month."""
    assert calver.next_version(["2026.11.1"], 2026, 11) == "2026.11.2"
    assert calver.next_version(["2026.11.1", "2026.11.2"], 2026, 11) == "2026.11.3"
    assert calver.next_version(["v2026.11.1"], 2026, 11) == "2026.11.2"


def test_next_version_restarts_the_counter_in_a_new_month(calver: ModuleType) -> None:
    """A new month counts from one again."""
    assert calver.next_version(["2026.10.9"], 2026, 11) == "2026.11.1"
    assert calver.next_version(["2026.11.2"], 2026, 12) == "2026.12.1"
    assert calver.next_version(["2026.11.2"], 2027, 1) == "2027.01.1"


def test_next_version_ignores_the_tags_of_other_projects(calver: ModuleType) -> None:
    """A tag that is not a CalVer tag does not count."""
    assert calver.next_version(["v1.0.0", "release-2026"], 2026, 11) == "2026.11.1"


def test_next_version_never_goes_back(calver: ModuleType) -> None:
    """The version is the greatest one of the repository."""
    assert calver.next_version(["2027.01.1"], 2026, 11) == "2027.01.2"


def test_a_commit_can_ask_for_no_release(calver: ModuleType) -> None:
    """The marker in the message of a commit skips the release."""
    assert calver.asks_for_no_release("docs: the contracts of the round [skip release]")
    assert calver.asks_for_no_release("docs: the contracts of the round\n\n[skip release]\n")


def test_a_commit_without_the_marker_is_released(calver: ModuleType) -> None:
    """Every other commit is released."""
    assert not calver.asks_for_no_release("docs: the contracts of the round")
    assert not calver.asks_for_no_release("fix: skip the release of the tag")


@pytest.fixture(scope="module")
def calver() -> ModuleType:
    """Load the script of the release workflow as a module."""
    spec = importlib.util.spec_from_file_location("calver", SCRIPT_FILE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
