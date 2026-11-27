"""Search in the ITU-T catalogue.

A search reads the structure of every study group and matches a text against
the codes and titles it holds. It is one responsibility of
:class:`ItuCatalogue`, separate from the lookups that name one entity.

The class implements :class:`~itu_t_documents.interfaces.CatalogueHost`, the
contract of the catalogue, so it can be mixed into :class:`ItuCatalogue`
without importing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from itu_t_documents.interfaces import CatalogueHost
from itu_t_documents.models.catalogue import StudyGroup
from itu_t_documents.models.study_periods import StudyPeriod


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


class SearchOperations(CatalogueHost):
    """The search method mixed into :class:`ItuCatalogue`."""

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
