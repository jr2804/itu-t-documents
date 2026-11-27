"""Parsers for the pages that describe the structure of the ITU-T.

The index page of a study period lists the study groups of the period, and
the structure page of a study group lists its plenary, its working groups,
its questions under study and its other groups.
"""

from __future__ import annotations

import re

from itu_t_documents.models.catalogue import PLENARY_CODE, StructureGroup, StudyGroupStructure
from itu_t_documents.models.documents import StudyGroup, StudyPeriod
from itu_t_documents.models.questions import Question, WorkingGroup
from itu_t_documents.scraping.pages import parse_page

#: Pattern of the link to the page of a study group of a study period.
_STUDY_GROUP_RE = re.compile(r"/studygroups/(?P<period>\d{4}-\d{4})/(?P<group>\d{1,2})/Pages/default\.aspx")

#: Pattern of the code of a question under study, e.g. ``Q5/12``.
_QUESTION_RE = re.compile(r"^Q(?P<number>\d+)/(?P<group>\d{1,2})$")

#: Pattern of the code of a working group, e.g. ``WP1/12``.
_WORKING_GROUP_RE = re.compile(r"^WP(?P<number>\d+)/(?P<group>\d{1,2})$")

#: Pattern of the code of a regional group, e.g. ``SG12RG-AFR``.
_REGIONAL_RE = re.compile(r"^SG\d{1,2}RG-[A-Z0-9]+$")

#: Pattern of the code of a focus group, e.g. ``FG-AINN``.
_FOCUS_RE = re.compile(r"^FG-[A-Z0-9]+$")

#: Pattern of the code of an intersector rapporteur group, e.g. ``IRG-AVQA``.
_RAPPORTEUR_RE = re.compile(r"^IRG-[A-Z0-9]+$")

#: Pattern of the code of a joint coordination activity, e.g. ``JCA-IMT2020``.
_COORDINATION_RE = re.compile(r"^JCA-[A-Z0-9/]+$")

#: Pattern of the code of a quality study group, e.g. ``QSDG``.
_STUDY_GROUP_NAME_RE = re.compile(r"^QSDG$")

#: The headings that separate the other groups of a study group.
_CATEGORY_RE = re.compile(r"^(?:Regional groups|Focus [Gg]roups|Other groups(?: under SG\d{1,2})?)$")


def parse_study_groups(page_html: str, period: StudyPeriod) -> list[StudyGroup]:
    """Parse the study groups of a study period.

    Args:
        page_html: The HTML of the index page of the study period.
        period: The study period the page belongs to.

    Returns:
        The study groups of the period, ordered by their number.
    """
    tree = parse_page(page_html)
    if tree is None:
        return []
    numbers: set[int] = set()
    for link in tree.xpath("//a[@href]"):
        match = _STUDY_GROUP_RE.search(link.get("href") or "")
        if match is None or match["period"] != period.label:
            continue
        numbers.add(int(match["group"]))
    return [StudyGroup(number=number, period=period) for number in sorted(numbers)]


def _classify(code: str) -> str | None:
    """Return the kind of the group with the given code, or ``None``."""
    if _REGIONAL_RE.match(code):
        return "regional"
    if _FOCUS_RE.match(code):
        return "focus"
    if _RAPPORTEUR_RE.match(code):
        return "rapporteur"
    if _COORDINATION_RE.match(code):
        return "coordination"
    if _STUDY_GROUP_NAME_RE.match(code):
        return "study"
    return None


def parse_structure(page_html: str, study_group: StudyGroup) -> StudyGroupStructure:
    """Parse the structure of a study group.

    Args:
        page_html: The HTML of the structure page of the study group.
        study_group: The study group the page belongs to.

    Returns:
        The plenary, the working groups, the questions under study and the
        other groups of the study group.
    """
    tree = parse_page(page_html)
    if tree is None:
        return StudyGroupStructure(study_group=study_group)

    plenary: WorkingGroup | None = None
    working_groups: list[WorkingGroup] = []
    questions: list[Question] = []
    other_groups: list[StructureGroup] = []
    current: WorkingGroup | None = None

    for row in tree.xpath("//tr"):
        cells = row.xpath("./td")
        if len(cells) < 2:
            continue
        code = _clean(cells[0].text_content())
        title = _clean(cells[1].text_content())
        if not code or code.lower().startswith("export"):
            continue

        if _CATEGORY_RE.match(code) is not None:
            continue

        if code == PLENARY_CODE:
            current = WorkingGroup(code=PLENARY_CODE, name=PLENARY_CODE)
            plenary = current
            continue

        question_match = _QUESTION_RE.match(code)
        if question_match is not None:
            questions.append(
                Question(
                    number=int(question_match["number"]),
                    study_group=study_group.number,
                    title=title,
                    working_group=current or WorkingGroup(code=PLENARY_CODE, name=PLENARY_CODE),
                )
            )
            continue

        working_group_match = _WORKING_GROUP_RE.match(code)
        if working_group_match is not None:
            current = WorkingGroup(code=code, name=title or code)
            working_groups.append(current)
            continue

        kind = _classify(code)
        if kind is not None:
            other_groups.append(StructureGroup(code=code, title=title, kind=kind))

    return StudyGroupStructure(
        study_group=study_group,
        plenary=plenary,
        working_groups=working_groups,
        questions=questions,
        other_groups=other_groups,
    )


def _clean(text: str) -> str:
    """Normalise the whitespace of a scraped text fragment."""
    return re.sub(r"\s+", " ", text).strip()
