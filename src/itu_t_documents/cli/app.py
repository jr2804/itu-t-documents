"""Cyclopts CLI app for ITU-T Documents."""

from __future__ import annotations

from cyclopts import App

from itu_t_documents.__about__ import __version__
from itu_t_documents.cli import commands

app = App(
    name="itu-t-documents",
    help="Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.",
    version=__version__,
    version_flags=["--version", "-v"],
)

# Register commands. Commands are plain functions in commands.py — no
# @app.command decorators there, no import of `app`: this avoids the
# circular import (commands.py <-> app.py) and keeps pyreorder from
# re-sorting this file into a broken state.
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
app.default(commands.default)  # `itu-t-documents` with no arguments

# Enable `itu-t-documents --install-completion`.
app.register_install_completion_command()


def main() -> None:
    """Entry point for the CLI application."""
    app()
