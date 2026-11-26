"""CLI arguments, options, and flags for ITU-T Document Downloader."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter
from cyclopts.types import StdioPath

# Application name for environment variables
APP_NAME_UPPERCASE = "ITU_DOC_DOWNLOADER"

# Global options

OutputFile = Annotated[
    str | None,
    Parameter(
        name="--output-file",
        alias="-o",
        help="Path to output file",
        env_var=f"{APP_NAME_UPPERCASE}_OUTPUT_FILE",
    ),
]

Cache = Annotated[
    bool,
    Parameter(
        help="Enable or disable caching",
        env_var=f"{APP_NAME_UPPERCASE}_CACHE",
    ),
]

# Command-specific arguments

NameArg = Annotated[
    str,
    Parameter(help="Name to greet"),
]

InputFileArg = Annotated[
    StdioPath | None,
    Parameter(
        name="--input-file",
        help='File containing names to greet (one per line, "-" for stdin)',
    ),
]

NumberArg1 = Annotated[
    float,
    Parameter(help="First number"),
]

NumberArg2 = Annotated[
    float,
    Parameter(help="Second number"),
]
