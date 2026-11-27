"""Tests for the recorded-pages test double."""

from __future__ import annotations

from pathlib import Path

from itu_t_documents.scraping.listing import parse_total_items
from tests.fakes import FakeClient


def test_fake_listing_can_keep_a_reported_count(fixtures_dir: Path) -> None:
    """The fake can reproduce a listing that reports more than it holds."""
    fake = FakeClient(fixtures_dir)

    page = fake._listing("listing_contributions.html", reported_count=85)

    assert parse_total_items(page) == 85
    fake.close()


def test_fake_listing_defaults_to_the_rows_it_holds(fixtures_dir: Path) -> None:
    """By default the fake reports the number of rows of the fixture."""
    fake = FakeClient(fixtures_dir)

    page = fake._listing("listing_contributions.html")

    assert parse_total_items(page) == page.count('name="chkFile"')
    fake.close()
