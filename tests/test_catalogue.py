"""Tests for the catalogue of the ITU-T study groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_t_documents.catalogue import CatalogueEntry, ItuCatalogue
from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import UnknownEntityError
from itu_t_documents.models.study_periods import StudyPeriod
from tests.fakes import FakeClient

PERIOD = StudyPeriod(start_year=2025, end_year=2028)


def test_periods(catalogue: ItuCatalogue) -> None:
    """The catalogue knows every study period of the ITU-T."""
    labels = [period.label for period in catalogue.periods()]

    assert "2025-2028" in labels
    assert len(labels) == 7


def test_current_period(catalogue: ItuCatalogue) -> None:
    """The catalogue knows the study period of the current year."""
    assert catalogue.current_period() == StudyPeriod.current()


def test_study_groups(catalogue: ItuCatalogue) -> None:
    """The study groups of a period are read from the index page."""
    groups = catalogue.study_groups(PERIOD)

    assert [group.code for group in groups] == ["SG02", "SG03", "SG05", "SG11", "SG12", "SG13", "SG15", "SG17", "SG20", "SG21"]
    assert all(group.period == PERIOD for group in groups)


def test_find_study_group(catalogue: ItuCatalogue) -> None:
    """A study group of the period is found."""
    group = catalogue.find_study_group(12, PERIOD)

    assert group.code == "SG12"
    assert group.number == 12
    assert group.label == "SG12 (2025-2028)"


def test_find_an_unknown_study_group(catalogue: ItuCatalogue) -> None:
    """A study group the period does not have is refused."""
    with pytest.raises(UnknownEntityError):
        catalogue.find_study_group(9, PERIOD)


def test_structure(catalogue: ItuCatalogue) -> None:
    """The structure of a study group holds its groups and questions."""
    structure = catalogue.structure(12, PERIOD)

    assert structure.study_group.code == "SG12"
    assert structure.period == PERIOD
    assert structure.plenary is not None
    assert structure.plenary.code == "PLEN"
    assert [group.code for group in structure.working_groups] == ["WP1/12", "WP2/12", "WP3/12"]
    assert structure.question(5).code == "Q5/12"
    assert structure.question(5).working_group.code == "WP1/12"
    assert structure.question(1).working_group.code == "PLEN"


def test_structure_of_an_unknown_study_group(catalogue: ItuCatalogue) -> None:
    """The structure of a study group that does not exist is refused."""
    with pytest.raises(UnknownEntityError):
        catalogue.structure(9, PERIOD)


def test_find_working_group(catalogue: ItuCatalogue) -> None:
    """A working group is found by its code."""
    working_group = catalogue.find_working_group("WP1/12", PERIOD)

    assert working_group.code == "WP1/12"


def test_find_an_unknown_working_group(catalogue: ItuCatalogue) -> None:
    """A working group the study group does not have is refused."""
    with pytest.raises(UnknownEntityError):
        catalogue.find_working_group("WP9/12", PERIOD)


def test_find_a_code_without_a_study_group(catalogue: ItuCatalogue) -> None:
    """A code that names no study group is refused."""
    with pytest.raises(UnknownEntityError):
        catalogue.find_working_group("PLEN", PERIOD)


def test_find_question(catalogue: ItuCatalogue) -> None:
    """A question under study is found by its number."""
    question = catalogue.find_question(5, PERIOD)

    assert question.code == "Q5/12"


def test_find_an_unknown_question(catalogue: ItuCatalogue) -> None:
    """A question no study group has is refused."""
    with pytest.raises(UnknownEntityError):
        catalogue.find_question(999, PERIOD)


def test_search(catalogue: ItuCatalogue) -> None:
    """The search finds the groups that mention the text."""
    entries = catalogue.search("speech", PERIOD)

    assert entries
    assert all("speech" in f"{entry.code} {entry.title}".lower() for entry in entries)
    assert {entry.study_group for entry in entries} <= {group.number for group in catalogue.study_groups(PERIOD)}


def test_search_finds_a_working_group(catalogue: ItuCatalogue) -> None:
    """The search finds a working group by its title."""
    entries = catalogue.search("Terminals", PERIOD)

    working_groups = [entry for entry in entries if entry.kind == "working group"]
    assert [entry.code for entry in working_groups] == ["WP1/12"]


def test_search_finds_a_regional_group(catalogue: ItuCatalogue) -> None:
    """The search finds a regional group by its title."""
    entries = catalogue.search("Regional", PERIOD)

    assert entries
    assert all(entry.kind == "regional" for entry in entries)


def test_search_finds_a_focus_group(catalogue: ItuCatalogue) -> None:
    """The search finds a focus group."""
    entries = catalogue.search("Artificial Intelligence Native", PERIOD)

    assert [entry.code for entry in entries] == ["FG-AINN"]
    assert entries[0].kind == "focus"


def test_an_entry_without_a_title_shows_its_code(catalogue: ItuCatalogue) -> None:
    """An entry without a title is shown by its code."""
    entry = CatalogueEntry(kind="question", code="Q5/12", title="", study_group=12, period="2025-2028")

    assert entry.label == "Q5/12"


def test_the_catalogue_is_a_context_manager(tmp_path: Path, fake_client: FakeClient) -> None:
    """The catalogue can be used as a context manager."""
    with ItuCatalogue(Settings(cache_dir=tmp_path), client=fake_client) as catalogue:
        assert catalogue.study_groups(PERIOD)


def test_search_without_a_match(catalogue: ItuCatalogue) -> None:
    """A search without a match yields nothing."""
    assert catalogue.search("nothing-at-all", PERIOD) == []


def test_search_with_an_empty_text(catalogue: ItuCatalogue) -> None:
    """A search without a text yields nothing."""
    assert catalogue.search("   ", PERIOD) == []


def test_the_catalogue_closes_the_client_it_owns(tmp_path: Path) -> None:
    """A catalogue without a client of its own closes it."""
    catalogue = ItuCatalogue(Settings(cache_dir=tmp_path))

    catalogue.close()


@pytest.fixture
def catalogue(tmp_path: Path, fake_client: FakeClient) -> ItuCatalogue:
    """Return a catalogue backed by the recorded fixtures."""
    return ItuCatalogue(Settings(cache_dir=tmp_path), client=fake_client)
