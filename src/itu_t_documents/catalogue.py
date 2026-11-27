"""The catalogue of the ITU-T study groups.

The catalogue knows the study periods, the study groups of a period and the
structure of a study group — its plenary, its working groups, its questions
under study and its other groups. The study groups and the questions change
from period to period, so they are read from the ITU-T and never hard coded.

Every entity of the catalogue can be looked up by its code, and a lookup
that names an entity the ITU-T does not have raises
:class:`~itu_t_documents.errors.UnknownEntityError` instead of returning
something that does not exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import UnknownEntityError
from itu_t_documents.http.client import ItuClient, ItuHttpClient
from itu_t_documents.models.catalogue import StudyGroupStructure
from itu_t_documents.models.documents import StudyGroup, StudyPeriod
from itu_t_documents.models.questions import Question, WorkingGroup
from itu_t_documents.scraping import catalogue as catalogue_scraper
from itu_t_documents.urls import period_index, structure_url, study_groups_index_url


@dataclass(frozen=True)
class CatalogueEntry:
    """One entry of a search in the catalogue."""

    kind: str
    code: str
    title: str
    study_group: int
    period: str

    @property
    def label(self) -> str:
        """The entry as it is shown to a user."""
        return f"{self.code} — {self.title}" if self.title else self.code


class ItuCatalogue:
    """The structure of the ITU-T study groups."""

    def __init__(self, settings: Settings | None = None, *, client: ItuClient | None = None) -> None:
        """Create the catalogue.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
            client: The HTTP client to use. Defaults to a new one.
        """
        self.settings = settings or Settings()
        self.client = client or ItuHttpClient(self.settings)
        self._owns_client = client is None

    def close(self) -> None:
        """Release the resources owned by this catalogue."""
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> ItuCatalogue:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Study periods
    # ------------------------------------------------------------------

    @staticmethod
    def periods() -> list[StudyPeriod]:
        """Return every study period the ITU-T knows, oldest first."""
        return StudyPeriod.all()

    @staticmethod
    def current_period() -> StudyPeriod:
        """Return the study period of the current year."""
        return StudyPeriod.current()

    # ------------------------------------------------------------------
    # Study groups
    # ------------------------------------------------------------------

    def study_groups(self, period: StudyPeriod) -> list[StudyGroup]:
        """Return the study groups of a study period.

        The study groups change from period to period, so they are read from
        the index page of the period.

        Args:
            period: The study period.

        Returns:
            The study groups of the period, ordered by their number.
        """
        page = self.client.get_text(study_groups_index_url(period))
        return catalogue_scraper.parse_study_groups(page, period)

    def find_study_group(self, number: int, period: StudyPeriod) -> StudyGroup:
        """Return a study group of a study period.

        Args:
            number: The number of the study group, e.g. 12.
            period: The study period.

        Returns:
            The study group.

        Raises:
            UnknownEntityError: When the period has no such study group.
        """
        study_groups = self.study_groups(period)
        for study_group in study_groups:
            if study_group.number == number:
                return study_group
        known = ", ".join(group.code for group in study_groups)
        raise UnknownEntityError(f"{period.label} has no study group SG{number:02d}; its study groups are {known}")

    # ------------------------------------------------------------------
    # Structure of a study group
    # ------------------------------------------------------------------

    def structure(self, study_group: int, period: StudyPeriod) -> StudyGroupStructure:
        """Return the structure of a study group.

        Args:
            study_group: The number of the study group, e.g. 12.
            period: The study period.

        Returns:
            The plenary, the working groups, the questions under study and
            the other groups of the study group.

        Raises:
            UnknownEntityError: When the period has no such study group.
        """
        group = self.find_study_group(study_group, period)
        page = self.client.get_text(structure_url(study_group, period_index(period)))
        return catalogue_scraper.parse_structure(page, group)

    def find_working_group(self, code: str, period: StudyPeriod) -> WorkingGroup:
        """Return a working group of a study group.

        The study group is taken from the code, e.g. ``WP1/12``.

        Args:
            code: The code of the working group, e.g. ``WP1/12``.
            period: The study period.

        Returns:
            The working group.

        Raises:
            UnknownEntityError: When the code names no working group, or the
                study group of the code has no such working group.
        """
        number = _study_group_of(code, "working group")
        for working_group in self.structure(number, period).working_groups:
            if working_group.code == code.strip().upper():
                return working_group
        raise UnknownEntityError(f"SG{number:02d} has no working group {code.strip().upper()}")

    def find_question(self, number: int, period: StudyPeriod, study_group: int | None = None) -> Question:
        """Return a question under study of a study group.

        A question number is only unique inside a study group, so the study
        group may be named. Without it every study group of the period is
        searched.

        Args:
            number: The number of the question, e.g. 5 for ``Q5/12``.
            period: The study period.
            study_group: The number of the study group, e.g. 12.

        Returns:
            The question.

        Raises:
            UnknownEntityError: When no study group of the period has such a
                question.
        """
        groups = [group for group in self.study_groups(period) if study_group is None or group.number == study_group]
        for group in groups:
            for question in self.structure(group.number, period).questions:
                if question.number == number:
                    return question
        raise UnknownEntityError(f"no study group of {period.label} has a question Q{number}")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, text: str, period: StudyPeriod | None = None) -> list[CatalogueEntry]:
        """Search the catalogue for the entities that mention the given text.

        The study groups, the working groups, the questions under study and
        the other groups of every study group of the period are searched.

        Args:
            text: The text to look for, e.g. ``speech`` or ``Q5``.
            period: The study period to search in. Defaults to the current
                study period.

        Returns:
            The matching entries, ordered by their kind and their code.
        """
        wanted = text.strip().lower()
        if not wanted:
            return []
        period = period or self.current_period()
        entries: list[CatalogueEntry] = []
        for study_group in self.study_groups(period):
            entries.extend(self._search_study_group(study_group, wanted))
        return sorted(entries, key=lambda entry: (entry.kind, entry.code))

    def _search_study_group(self, study_group: StudyGroup, wanted: str) -> list[CatalogueEntry]:
        """Return the entries of a study group that mention the given text."""
        entries: list[CatalogueEntry] = []
        structure = self.structure(study_group.number, study_group.period)
        for working_group in structure.working_groups:
            if _matches(wanted, working_group.code, working_group.name):
                entries.append(
                    CatalogueEntry(
                        kind="working group",
                        code=working_group.code,
                        title=working_group.name or "",
                        study_group=study_group.number,
                        period=study_group.period.label,
                    )
                )
        for question in structure.questions:
            if _matches(wanted, question.code, question.title):
                entries.append(
                    CatalogueEntry(
                        kind="question",
                        code=question.code,
                        title=question.title,
                        study_group=study_group.number,
                        period=study_group.period.label,
                    )
                )
        for group in structure.other_groups:
            if _matches(wanted, group.code, group.title):
                entries.append(
                    CatalogueEntry(
                        kind=group.kind or "group",
                        code=group.code,
                        title=group.title,
                        study_group=study_group.number,
                        period=study_group.period.label,
                    )
                )
        return entries


def _matches(wanted: str, code: str, title: str | None) -> bool:
    """Whether the code or the title of an entity mentions the given text."""
    return wanted in code.lower() or (title is not None and wanted in title.lower())


def _study_group_of(code: str, kind: str) -> int:
    """Return the study group of a working group or question code.

    Args:
        code: The code of the entity, e.g. ``WP1/12``.
        kind: The kind of the entity, used in the error message.

    Returns:
        The number of the study group.

    Raises:
        UnknownEntityError: When the code carries no study group.
    """
    match = re.match(r"^[A-Z]+(?P<number>\d+)/(?P<group>\d{1,2})$", code.strip().upper())
    if match is None:
        raise UnknownEntityError(f"{code!r} is not the code of a {kind}, e.g. WP1/12")
    return int(match["group"])
