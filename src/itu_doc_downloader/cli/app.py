"""Cyclopts CLI app for ITU-T Document Downloader."""

from __future__ import annotations

from importlib.metadata import version

from cyclopts import App

from itu_doc_downloader.cli import commands


# Version management
def _get_version() -> str:
    """Get application version from package metadata."""
    try:
        return version("itu-doc-downloader")
    except Exception:
        return "0.0.0"  # Fallback for development mode


app = App(
    name="itu-doc-downloader",
    help="Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP.",
    version=_get_version,
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
app.default(commands.default)  # `itu-doc-downloader` with no arguments

# Enable `itu-doc-downloader --install-completion`.
app.register_install_completion_command()


def main() -> None:
    """Entry point for the CLI application."""
    app()
