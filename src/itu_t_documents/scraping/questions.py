"""Parser for the ITU-T "List of Questions and Rapporteurs" pages.

The page lists every question under study of a study group together with the
people holding a rapporteur role for it. Each question occupies a table row
pair: the first cell names the question and its working group, the second cell
holds one person.
"""

from __future__ import annotations

import re

from lxml.html import HtmlElement

from itu_t_documents.models.enums import Role
from itu_t_documents.models.questions import Person, Question, WorkingGroup
from itu_t_documents.scraping.pages import parse_page

#: Pattern of the question and working group cell, e.g. ``Q5/12  (WP1/12)``.
_QUESTION_RE = re.compile(r"Q(?P<number>\d+)\s*/\s*(?P<group>\d+)\s*(?:\((?P<working_group>[^)]+)\))?")

#: Roles the ITU-T pages use, mapped onto the domain enum.
_ROLE_NAMES: dict[str, Role] = {
    "rapporteur": Role.RAPPORTEUR,
    "co-rapporteur": Role.CO_RAPPORTEUR,
    "associate rapporteur": Role.ASSOCIATE_RAPPORTEUR,
    "editor": Role.EDITOR,
}


def _clean(text: str) -> str:
    """Normalise whitespace of a scraped text fragment."""
    return re.sub(r"\s+", " ", text).strip()


def _text_with_breaks(element: HtmlElement) -> str:
    """Return the text of an element, turning ``<br>`` into line breaks."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.tag == "br":
            parts.append("\n")
        else:
            parts.append(_text_with_breaks(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _span_text(cell: HtmlElement, marker: str) -> str:
    """Return the text of the first span whose id contains ``marker``."""
    found = cell.xpath(f".//span[contains(@id, '{marker}')]")
    if not found:
        return ""
    return _clean(_text_with_breaks(found[0]))


def _last_line(text: str) -> str:
    """Return the last non-empty line of a scraped text fragment."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def parse_questions(page_html: str, study_group: int) -> list[Question]:
    """Parse the questions under study of a study group.

    Args:
        page_html: The HTML of the questions page.
        study_group: The study group the page belongs to.

    Returns:
        The questions found, ordered by question number.
    """
    tree = parse_page(page_html)
    if tree is None:
        return []
    people: dict[int, list[Person]] = {}
    titles: dict[int, str] = {}
    working_groups: dict[int, str] = {}

    for row in tree.xpath("//tr"):
        cells = row.xpath("./td")
        if len(cells) < 2:
            continue
        header = cells[0].xpath(".//span[contains(@id, 'lblQWP')]")
        if not header:
            continue
        match = _QUESTION_RE.search(_clean(header[0].text_content()))
        if match is None:
            continue
        number = int(match["number"])
        titles.setdefault(number, _span_text(cells[0], "lblQuestion"))
        working_groups.setdefault(number, (match["working_group"] or "PLEN").strip())

        person = _parse_person(cells[1])
        if person is not None:
            people.setdefault(number, []).append(person)

    questions = [
        Question(
            number=number,
            study_group=study_group,
            title=titles.get(number, ""),
            working_group=WorkingGroup.parse(working_groups.get(number, "PLEN")),
            people=people.get(number, []),
        )
        for number in sorted(titles)
    ]
    return questions


def _parse_person(cell: HtmlElement) -> Person | None:
    """Parse the person cell of a question row."""
    first_name = _span_text(cell, "lblFName")
    last_name = _span_text(cell, "lblLName")
    name = _clean(f"{first_name} {last_name}")
    role_text = _span_text(cell, "lblRole")
    if not name or not role_text:
        return None

    email = ""
    links = cell.xpath(".//a[contains(@id, 'linkemail')]")
    if links:
        href = links[0].get("href") or ""
        email = href.removeprefix("mailto:").strip()
    else:
        email = _span_text(cell, "linkemail").replace("[at]", "@")

    address = cell.xpath(".//span[contains(@id, 'lblAddress')]")
    country = _last_line(_text_with_breaks(address[0])) if address else None

    return Person(
        name=name,
        role=_ROLE_NAMES.get(role_text.lower(), Role.CONTRIBUTOR),
        organization=_span_text(cell, "lblCompany") or None,
        country=country or None,
        email=email or None,
        phone=_span_text(cell, "telLabel") or None,
        fax=_span_text(cell, "faxLabel") or None,
    )
