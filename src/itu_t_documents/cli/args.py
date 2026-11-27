"""CLI arguments, options, and flags for ITU-T Documents."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any

from cyclopts import Parameter

from itu_t_documents.models.enums import DocFormat, DocLanguage, DocType

APP_NAME_UPPERCASE = "ITU_T_DOCUMENTS"


def _enum_value(enum_type: type[DocFormat] | type[DocLanguage] | type[DocType], tokens: Sequence[Any]) -> Any:
    """Convert the value cyclopts parsed into the enumeration member."""
    return enum_type(str(tokens[0].value).upper())


StudyGroup = Annotated[
    int,
    Parameter(
        name="--study-group",
        alias="-g",
        help="Study group number, e.g. 12",
        env_var=f"{APP_NAME_UPPERCASE}_STUDY_GROUP",
    ),
]

StudyPeriod = Annotated[
    str | None,
    Parameter(
        name="--study-period",
        alias="-p",
        help="Study period, e.g. 2025-2028. Defaults to the current study period.",
        env_var=f"{APP_NAME_UPPERCASE}_STUDY_PERIOD",
    ),
]

StudyPeriodFilter = Annotated[
    str | None,
    Parameter(
        name="--study-period",
        alias="-p",
        help="Study period, e.g. 2025-2028. Defaults to every study period.",
        env_var=f"{APP_NAME_UPPERCASE}_STUDY_PERIOD",
    ),
]

Meeting = Annotated[
    str,
    Parameter(
        name="--meeting",
        alias="-m",
        help="Meeting code as used by the ITU-T, e.g. 270119",
        env_var=f"{APP_NAME_UPPERCASE}_MEETING",
    ),
]

DocTypeOption = Annotated[
    DocType | None,
    Parameter(
        name="--type",
        choices=[doc_type.value for doc_type in DocType],
        converter=lambda _type, tokens: _enum_value(DocType, tokens),
        show_default=False,
        help="Document type: TD (temporary document), C (contribution), COL (collective letter), R (report)",
    ),
]

Question = Annotated[
    int | None,
    Parameter(
        name="--question",
        alias="-q",
        help="Restrict to a question number, e.g. 5 for Q5/12",
    ),
]

Source = Annotated[
    str | None,
    Parameter(
        name="--source",
        alias="-s",
        help="Restrict to a submitting organisation; the match is partial",
    ),
]

Limit = Annotated[
    int | None,
    Parameter(
        name="--limit",
        alias="-l",
        help="Maximum number of results",
    ),
]

LastMeetings = Annotated[
    int,
    Parameter(
        name="--last-meetings",
        help="How many of the most recent meetings to count",
    ),
]

DocumentId = Annotated[
    str,
    Parameter(
        name="--document",
        help="Document identifier, e.g. T25-SG12-261015-TD-GEN-0520",
    ),
]

FileFormat = Annotated[
    DocFormat,
    Parameter(
        name="--format",
        choices=[file_format.value for file_format in DocFormat],
        converter=lambda _type, tokens: _enum_value(DocFormat, tokens),
        show_default=False,
        help="File format: PDF, MSW (Word), ZIP or HTM. Defaults to PDF.",
    ),
]

Language = Annotated[
    DocLanguage,
    Parameter(
        name="--language",
        choices=[language.value for language in DocLanguage],
        converter=lambda _type, tokens: _enum_value(DocLanguage, tokens),
        show_default=False,
        help="Language code: E (English), F (French), S (Spanish), A (Arabic), C (Chinese), R (Russian). Defaults to E.",
    ),
]

OutputFile = Annotated[
    str | None,
    Parameter(
        name="--output-file",
        alias="-o",
        help="Path to output file",
        env_var=f"{APP_NAME_UPPERCASE}_OUTPUT_FILE",
    ),
]

SearchText = Annotated[
    str,
    Parameter(
        name="--search",
        alias="-s",
        help="Text to look for, e.g. speech",
    ),
]
