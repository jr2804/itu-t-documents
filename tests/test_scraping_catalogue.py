"""Tests for the parsers of the pages that describe the ITU-T structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_t_documents.errors import UnknownEntityError
from itu_t_documents.models.catalogue import StructureGroup
from itu_t_documents.models.documents import StudyGroup, StudyPeriod
from itu_t_documents.scraping import catalogue

PERIOD = StudyPeriod(start_year=2025, end_year=2028)
OTHER_PERIOD = StudyPeriod(start_year=2022, end_year=2024)


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_parse_the_study_groups_of_a_period(fixtures_dir: Path) -> None:
    """The index page of a period yields its study groups."""
    page = _read(fixtures_dir, "study_groups_index.html")

    groups = catalogue.parse_study_groups(page, PERIOD)

    assert [group.code for group in groups] == ["SG02", "SG03", "SG05", "SG11", "SG12", "SG13", "SG15", "SG17", "SG20", "SG21"]


def test_parse_the_study_groups_of_another_period(fixtures_dir: Path) -> None:
    """The study groups of another period are not taken over."""
    page = _read(fixtures_dir, "study_groups_index.html")

    assert catalogue.parse_study_groups(page, OTHER_PERIOD) == []


def test_parse_the_study_groups_of_an_empty_page() -> None:
    """An empty page holds no study group."""
    assert catalogue.parse_study_groups("", PERIOD) == []


def test_parse_the_structure_of_a_study_group(fixtures_dir: Path) -> None:
    """The structure page yields the groups and the questions."""
    page = _read(fixtures_dir, "study_group_structure.html")

    structure = catalogue.parse_structure(page, StudyGroup(number=12, period=PERIOD))

    assert structure.plenary is not None
    assert structure.plenary.code == "PLEN"
    assert [group.code for group in structure.working_groups] == ["WP1/12", "WP2/12", "WP3/12"]
    assert [question.code for question in structure.questions][:3] == ["Q1/12", "Q2/12", "Q4/12"]
    assert structure.question(5).working_group.code == "WP1/12"
    assert structure.question(1).working_group.code == "PLEN"


def test_parse_the_structure_with_the_focus_groups(fixtures_dir: Path) -> None:
    """The focus groups and the coordination activities are found."""
    page = _read(fixtures_dir, "study_group_structure_13.html")

    structure = catalogue.parse_structure(page, StudyGroup(number=13, period=PERIOD))

    assert structure.plenary is None
    assert [(group.code, group.kind) for group in structure.other_groups] == [
        ("SG13RG-EECAT", "regional"),
        ("SG13RG-AFR", "regional"),
        ("FG-AINN", "focus"),
        ("JCA-IMT2020/IMT2030", "coordination"),
    ]
    assert structure.question(20).working_group.code == "WP1/13"


def test_parse_the_structure_of_an_empty_page() -> None:
    """An empty page holds no group."""
    structure = catalogue.parse_structure("", StudyGroup(number=12, period=PERIOD))

    assert structure.plenary is None
    assert structure.working_groups == []
    assert structure.questions == []


def test_parse_a_row_that_carries_no_group() -> None:
    """A row that names no group is left out."""
    page = "<html><body><table><tr><td>Export:</td><td></td></tr><tr><td>ACRONYM</td><td>TITLE</td></tr></table></body></html>"

    structure = catalogue.parse_structure(page, StudyGroup(number=12, period=PERIOD))

    assert structure.working_groups == []
    assert structure.other_groups == []


def test_the_structure_looks_a_working_group_up() -> None:
    """A working group of the structure is found by its code."""
    structure = catalogue.parse_structure(
        "<html><body><table><tr><td>WP1/12</td><td>A working group</td></tr></table></body></html>",
        StudyGroup(number=12, period=PERIOD),
    )

    assert structure.working_group("wp1/12").code == "WP1/12"


def test_the_structure_refuses_an_unknown_working_group() -> None:
    """A working group the study group does not have is refused."""
    structure = catalogue.parse_structure("", StudyGroup(number=12, period=PERIOD))

    with pytest.raises(UnknownEntityError, match="WP9/12"):
        structure.working_group("WP9/12")


def test_the_structure_refuses_an_unknown_question() -> None:
    """A question the study group does not have is refused."""
    structure = catalogue.parse_structure("", StudyGroup(number=12, period=PERIOD))

    with pytest.raises(UnknownEntityError, match="Q99/12"):
        structure.question(99)


def test_the_kind_of_a_group_is_told() -> None:
    """The kind of a group is known."""
    assert StructureGroup(code="SG12RG-AFR", kind="regional").is_regional
    assert not StructureGroup(code="SG12RG-AFR", kind="regional").is_focus
    assert StructureGroup(code="FG-AINN", kind="focus").is_focus
