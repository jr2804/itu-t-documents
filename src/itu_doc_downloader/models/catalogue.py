"""Domain model for the structure of an ITU-T study group.

The ITU-T publishes the structure of a study group on its "Structure" page:
the plenary, the working groups, the questions under study and the other
groups — regional groups, focus groups, intersector rapporteur groups and
the joint coordination activities. The groups change from study period to
study period, so they are read from the ITU-T and not hard coded.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from itu_doc_downloader.errors import UnknownEntityError
from itu_doc_downloader.models.documents import StudyGroup, StudyPeriod
from itu_doc_downloader.models.questions import Question, WorkingGroup

#: The code of the plenary of a study group.
PLENARY_CODE = "PLEN"


class StructureGroup(BaseModel):
    """A group of a study group that is neither a question nor a working group."""

    model_config = ConfigDict(frozen=True)

    code: str
    title: str = ""
    kind: str = ""

    @property
    def is_regional(self) -> bool:
        """Whether the group is a regional group."""
        return self.kind == "regional"

    @property
    def is_focus(self) -> bool:
        """Whether the group is a focus group."""
        return self.kind == "focus"


class StudyGroupStructure(BaseModel):
    """The structure of an ITU-T study group in a study period."""

    model_config = ConfigDict(frozen=True)

    study_group: StudyGroup
    plenary: WorkingGroup | None = None
    working_groups: list[WorkingGroup] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    other_groups: list[StructureGroup] = Field(default_factory=list)

    @property
    def period(self) -> StudyPeriod:
        """The study period the structure belongs to."""
        return self.study_group.period

    def working_group(self, code: str) -> WorkingGroup:
        """Return a working group of the study group.

        Args:
            code: The code of the working group, e.g. ``WP1/12``.

        Returns:
            The working group.

        Raises:
            UnknownEntityError: When the study group has no such working group.
        """
        wanted = code.strip().upper()
        for working_group in self.working_groups:
            if working_group.code == wanted:
                return working_group
        raise UnknownEntityError(f"{self.study_group.code} has no working group {wanted}")

    def question(self, number: int) -> Question:
        """Return a question under study of the study group.

        Args:
            number: The number of the question, e.g. 5 for ``Q5/12``.

        Returns:
            The question.

        Raises:
            UnknownEntityError: When the study group has no such question.
        """
        for question in self.questions:
            if question.number == number:
                return question
        raise UnknownEntityError(f"{self.study_group.code} has no question Q{number}/{self.study_group.number}")
