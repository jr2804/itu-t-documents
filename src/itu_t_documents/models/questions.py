"""Domain model for ITU-T questions under study.

A question under study belongs to exactly one study group and to one working
group (``WP1/12``, ``WP2/12``, …) or to the plenary (``PLEN``). The rapporteur
roles are published by the ITU-T "List of Questions and Rapporteurs" page.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from itu_t_documents.models.enums import PLENARY_CODE, Role


class WorkingGroup(BaseModel):
    """A working group of a study group, or the plenary itself."""

    model_config = ConfigDict(frozen=True)

    code: str
    name: str | None = None

    @property
    def is_plenary(self) -> bool:
        """Whether this working group is the plenary of the study group."""
        return self.code.upper() == PLENARY_CODE

    @classmethod
    def parse(cls, code: str) -> WorkingGroup:
        """Parse a working group code such as ``WP1/12``."""
        text = code.strip()
        name: str | None = None
        if "/" in text:
            group, _, number = text.partition("/")
            name = f"{group.upper()} {number}"
        return cls(code=text.upper(), name=name)


class Person(BaseModel):
    """A person holding a role for a question under study."""

    model_config = ConfigDict(frozen=True)

    name: str
    role: Role
    organization: str | None = None
    country: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None


class Question(BaseModel):
    """A question under study of an ITU-T study group."""

    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=0)
    study_group: int = Field(ge=1, le=99)
    title: str = ""
    working_group: WorkingGroup
    people: list[Person] = Field(default_factory=list)

    @property
    def code(self) -> str:
        """The ITU-T code of the question, e.g. ``Q5/12``."""
        return f"Q{self.number}/{self.study_group}"

    @property
    def rapporteurs(self) -> list[Person]:
        """The people holding a rapporteur role for this question."""
        return [person for person in self.people if person.role is Role.RAPPORTEUR]

    @property
    def co_rapporteurs(self) -> list[Person]:
        """The people holding a co-rapporteur role for this question."""
        return [person for person in self.people if person.role is Role.CO_RAPPORTEUR]
