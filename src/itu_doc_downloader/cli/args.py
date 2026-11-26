"""CLI arguments, options, and flags for ITU-T Document Downloader."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter

# Application name for environment variables
APP_NAME_UPPERCASE = "ITU_DOC_DOWNLOADER"

#: The study period used when the user does not name one.
DEFAULT_STUDY_PERIOD = "2025-2028"

# Global options

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
    str,
    Parameter(
        name="--study-period",
        alias="-p",
        help=f"Study period, e.g. {DEFAULT_STUDY_PERIOD}",
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
    str | None,
    Parameter(
        name="--type",
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

DocumentId = Annotated[
    str,
    Parameter(
        name="--document",
        help="Document identifier, e.g. T25-SG12-261015-TD-GEN-0520",
    ),
]

FileFormat = Annotated[
    str,
    Parameter(
        name="--format",
        help="File format: PDF, MSW (Word), ZIP or HTM",
    ),
]

Language = Annotated[
    str,
    Parameter(
        name="--language",
        help="Language code: E (English), F (French), S (Spanish), A (Arabic), C (Chinese), R (Russian)",
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
