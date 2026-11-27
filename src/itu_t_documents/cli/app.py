"""Cyclopts CLI app for ITU-T Documents."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import Any

import httpx
from cyclopts import App

from itu_t_documents.__about__ import __version__
from itu_t_documents.cli import commands
from itu_t_documents.errors import ItuError


class ItuApp(App):
    """The command line application, with one failure shape."""

    def __call__(self, tokens: None | str | Iterable[str] = None, **kwargs: Any) -> Any:
        """Run the application and turn domain failures into exit code 1.

        Cyclopts keeps the usage errors: an unknown option, a missing
        argument or a value outside the choices of an enumeration exits 2
        before a command runs.
        """
        try:
            return super().__call__(tokens, **kwargs)
        except (ItuError, ValueError, FileNotFoundError) as error:
            print(f"itu-t-documents: {error}", file=sys.stderr)
            raise SystemExit(1) from error
        except httpx.HTTPError as error:
            print(f"itu-t-documents: cannot reach the ITU-T: {error}", file=sys.stderr)
            raise SystemExit(1) from error


app = ItuApp(
    name="itu-t-documents",
    help="Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.",
    version=__version__,
    version_flags=["--version", "-v"],
)

app.command(commands.default, name="default")
app.command(commands.auth)
app.command(commands.download)
app.command(commands.documents)
app.command(commands.mcp)
app.command(commands.meetings)
app.command(commands.periods)
app.command(commands.questions)
app.command(commands.search)
app.command(commands.structure)
app.command(commands.study_groups, name="study-groups")
app.command(commands.sync)
app.command(commands.top_sources, name="top-sources")
app.default(commands.default)


def main() -> None:
    """Entry point for the CLI application."""
    app()
