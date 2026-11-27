"""The study periods of the ITU-T.

A document identifier names its study period by a two digit code, ``T25``
for ``2025-2028``. The periods are a closed registry: the ITU-T has had
seven of them since 2005 and they do not all span four years, so a period
is looked up in the registry and never computed from its code.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

#: The study periods of the ITU-T. A period spans four years and starts in
#: 2005, 2009, 2013, 2017, 2022, 2025 and 2029 — the period that was to start
#: in 2021 was renamed to 2022-2024, because the extra year was used for the
#: session that had been postponed.
STUDY_PERIODS: tuple[tuple[int, int], ...] = (
    (2005, 2008),
    (2009, 2012),
    (2013, 2016),
    (2017, 2020),
    (2022, 2024),
    (2025, 2028),
    (2029, 2032),
)


class StudyPeriod(BaseModel):
    """An ITU-T study period, e.g. ``2025-2028``.

    The ITU-T publishes a fixed set of study periods, so a period that the
    ITU-T does not know cannot be constructed.
    """

    model_config = ConfigDict(frozen=True)

    start_year: int = Field(ge=1900, le=2999)
    end_year: int = Field(ge=1900, le=2999)

    @property
    def code(self) -> str:
        """The DMS code for this period, e.g. ``T25``."""
        return f"T{self.start_year % 100:02d}"

    @property
    def short_code(self) -> str:
        """The two-digit start year used inside DMS download paths, e.g. ``25``."""
        return f"{self.start_year % 100:02d}"

    @property
    def label(self) -> str:
        """The human readable period, e.g. ``2025-2028``."""
        return f"{self.start_year}-{self.end_year}"

    @classmethod
    def all(cls) -> list[StudyPeriod]:
        """Return every study period the ITU-T knows, oldest first."""
        return [cls(start_year=start, end_year=end) for start, end in STUDY_PERIODS]

    @classmethod
    def from_year(cls, year: int) -> StudyPeriod:
        """Return the study period that starts in the given year.

        Args:
            year: The first year of the period, e.g. 2025.

        Returns:
            The study period, e.g. ``2025-2028``.

        Raises:
            ValueError: When the ITU-T has no study period that starts in the
                given year.
        """
        for start, end in STUDY_PERIODS:
            if start == year:
                return cls(start_year=start, end_year=end)
        known = ", ".join(str(start) for start, _ in STUDY_PERIODS)
        raise ValueError(f"the ITU-T has no study period starting in {year}; the periods start in {known}")

    @classmethod
    def containing(cls, year: int) -> StudyPeriod:
        """Return the study period the given year falls into.

        Args:
            year: The year, e.g. 2026.

        Returns:
            The study period, e.g. ``2025-2028``.

        Raises:
            ValueError: When no study period covers the given year.
        """
        for start, end in STUDY_PERIODS:
            if start <= year <= end:
                return cls(start_year=start, end_year=end)
        known = ", ".join(f"{start}-{end}" for start, end in STUDY_PERIODS)
        raise ValueError(f"the year {year} falls into no ITU-T study period; the known periods are {known}")

    @classmethod
    def current(cls) -> StudyPeriod:
        """Return the study period of the current year."""
        return cls.containing(date.today().year)

    @classmethod
    def parse(cls, value: str) -> StudyPeriod:
        """Parse ``"2025-2028"``, ``"T25"`` or the start year ``"2025"``."""
        text = value.strip()
        if text.upper().startswith("T") and text[1:].isdigit():
            return cls.from_year(2000 + int(text[1:]) if int(text[1:]) < 90 else 1900 + int(text[1:]))
        if text.isdigit():
            return cls.from_year(int(text))
        start_text, _, end_text = text.partition("-")
        if not end_text:
            raise ValueError(f"cannot parse study period from {value!r}")
        return cls(start_year=int(start_text), end_year=int(end_text))

    @model_validator(mode="after")
    def _check_known(self) -> StudyPeriod:
        """Ensure the ITU-T knows the period."""
        if (self.start_year, self.end_year) not in STUDY_PERIODS:
            known = ", ".join(f"{start}-{end}" for start, end in STUDY_PERIODS)
            raise ValueError(f"the ITU-T has no study period {self.start_year}-{self.end_year}; the known periods are {known}")
        return self

    @field_validator("end_year")
    @classmethod
    def _check_end_year(cls, value: int, info: ValidationInfo) -> int:
        """Ensure the period spans a sensible number of years."""
        start = info.data.get("start_year")
        if isinstance(start, int) and value < start:
            raise ValueError("end_year must not precede start_year")
        return value
