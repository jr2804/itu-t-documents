"""Tests for the parser of the questions under study."""

from __future__ import annotations

from pathlib import Path

import pytest

from itu_t_documents.errors import ScrapingError
from itu_t_documents.scraping import meetings, questions


def test_parse_questions_page(fixtures_dir: Path) -> None:
    """The questions page yields the questions with their working group and people."""
    page = _read(fixtures_dir, "questions.html")

    parsed = questions.parse_questions(page, 12)

    assert len(parsed) == 5
    first = parsed[0]
    assert first.code == "Q1/12"
    assert first.working_group.code == "PLEN"
    assert first.working_group.is_plenary
    assert first.people[0].name == "Seong-Ho JEONG"
    assert first.people[0].role.value == "Co-rapporteur"
    assert first.people[0].country == "Korea (Rep. of)"

    question_five = next(item for item in parsed if item.number == 5)
    assert question_five.working_group.code == "WP1/12"
    assert question_five.rapporteurs[0].name == "Lars Birger NIELSEN"
    assert question_five.rapporteurs[0].country == "Denmark"

    question_four = next(item for item in parsed if item.number == 4)
    assert question_four.rapporteurs[0].email == "jan.reimes@head-acoustics.de"


def test_questions_refuse_an_unknown_role() -> None:
    """A person is never given a role the page did not state."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP1">Q1/12</span><span id="lblQuestion1">Q1</span></td>'
        '<td><span id="lblFName1">Ada</span><span id="lblLName1">LOVELACE</span>'
        '<span id="lblRole1">Observer</span></td></tr></table></body></html>'
    )

    with pytest.raises(ScrapingError, match="question person"):
        questions.parse_questions(page, 12)


def test_questions_refuse_a_person_without_a_name() -> None:
    """A named role without a name is reported."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP1">Q1/12</span></td>'
        '<td><span id="lblRole1">Rapporteur</span></td></tr></table></body></html>'
    )

    with pytest.raises(ScrapingError, match="question person"):
        questions.parse_questions(page, 12)


def test_parse_question_numbers(fixtures_dir: Path) -> None:
    """The meeting index lists the questions of the study group."""
    page = _read(fixtures_dir, "meeting_index.html")

    assert meetings.parse_question_numbers(page)[:3] == [1, 2, 4]


def _read(fixtures_dir: Path, name: str) -> str:
    """Return the content of a recorded fixture."""
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_parse_questions_of_a_page_without_questions() -> None:
    """A page without questions yields no question."""
    assert questions.parse_questions("<html><body>nothing</body></html>", 12) == []


def test_parse_question_numbers_of_a_page_without_questions() -> None:
    """A page without questions yields no question number."""
    assert meetings.parse_question_numbers("<html><body>nothing</body></html>") == []


def test_parse_questions_with_an_unknown_role() -> None:
    """A role that the ITU-T pages do not know is refused."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12  (PLEN)</span>'
        '<span id="lblQuestion_1">A question</span></td>'
        '<td><span id="lblFName_1">Ada</span><span id="lblLName_1">LOVELACE</span>'
        '<span id="lblRole_1">Observer</span></td></tr></table></body></html>'
    )

    with pytest.raises(ScrapingError, match="question person"):
        questions.parse_questions(page, 12)


def test_parse_questions_without_a_person() -> None:
    """A question without a person yields no person."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12  (PLEN)</span><span id="lblQuestion_1">A question</span></td><td></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert len(parsed) == 1
    assert parsed[0].people == []


def test_parse_questions_skips_a_row_without_a_question_number() -> None:
    """A row whose question code cannot be read is ignored."""
    page = '<html><body><table><tr><td><span id="lblQWP_1">not a question</span></td><td></td></tr></table></body></html>'

    assert questions.parse_questions(page, 12) == []


def test_parse_questions_of_a_row_without_working_group() -> None:
    """A question without a working group falls back to the plenary."""
    page = (
        '<html><body><table><tr><td><span id="lblQWP_1">Q1/12</span>'
        '<span id="lblQuestion_1">A question</span></td>'
        '<td><span id="lblFName_1">Ada</span><span id="lblLName_1">LOVELACE</span>'
        '<span id="lblRole_1">Rapporteur</span></td></tr></table></body></html>'
    )

    parsed = questions.parse_questions(page, 12)

    assert parsed[0].working_group.code == "PLEN"
