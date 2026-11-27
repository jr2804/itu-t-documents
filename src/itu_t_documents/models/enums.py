"""Domain enumerations for ITU-T meeting documents.

The ITU-T document management system (DMS) encodes every concept in short
upper-case codes. Those codes are the wire format, so they are modelled as
:class:`enum.StrEnum` members instead of being scattered as string literals.
"""

from __future__ import annotations

from enum import StrEnum


class DocFormat(StrEnum):
    """File formats offered by the ITU-T DMS for a document.

    The member value is the code used in the ``!!<FORMAT>-<LANGUAGE>`` suffix
    of a download URL.
    """

    WORD = "MSW"
    PDF = "PDF"
    ZIP = "ZIP"
    HTML = "HTM"

    @classmethod
    def parse(cls, code: str) -> DocFormat | None:
        """Return the member for ``code`` or ``None`` when the code is unknown."""
        try:
            return cls(code.strip().upper())
        except ValueError:
            return None


class DocLanguage(StrEnum):
    """Languages a document can be published in.

    The member value is the code used in the ``!!<FORMAT>-<LANGUAGE>`` suffix
    of a download URL.
    """

    ENGLISH = "E"
    FRENCH = "F"
    SPANISH = "S"
    ARABIC = "A"
    CHINESE = "C"
    RUSSIAN = "R"

    @classmethod
    def parse(cls, code: str) -> DocLanguage | None:
        """Return the member for ``code`` or ``None`` when the code is unknown."""
        try:
            return cls(code.strip().upper())
        except ValueError:
            return None


class DocType(StrEnum):
    """Document type codes as they appear in ITU-T document identifiers.

    ``C``
        Contribution submitted to a study group.
    ``TD``
        Temporary document produced during a meeting.
    ``COL``
        Collective letter (circular) issued by a study group.
    ``R``
        Report produced by a study group.
    """

    CONTRIBUTION = "C"
    TEMPORARY_DOCUMENT = "TD"
    COLLECTIVE_LETTER = "COL"
    REPORT = "R"


class DocVisibility(StrEnum):
    """Access level of a document in the ITU-T DMS.

    The ITU-T DMS exposes documents under three different path prefixes.
    ``PUBLIC`` documents are downloadable without a TIES account, the other
    two require an authenticated session. The member value is the path
    segment used by the ITU-T download URLs.
    """

    PUBLIC = "pub"
    TIES = "ties"
    INTERNAL = "inf"


class Role(StrEnum):
    """Roles a person can hold for a question under study."""

    RAPPORTEUR = "Rapporteur"
    CO_RAPPORTEUR = "Co-rapporteur"
    ASSOCIATE_RAPPORTEUR = "Associate rapporteur"
    EDITOR = "Editor"
    CONTRIBUTOR = "Contributor"
