"""The commands that start the package, the server or a login.

These commands do not read a document; they introduce the package, run the
MCP server and check the TIES credentials.
"""

from __future__ import annotations

from importlib import import_module

from itu_t_documents.config.settings import Settings
from itu_t_documents.errors import AuthenticationError
from itu_t_documents.http.client import ItuHttpClient


def default() -> None:
    """Show a short introduction to the ITU-T documents."""
    print("itu-t-documents — access the documents of ITU-T study group meetings.")
    print("Use --help to see the available commands.")


def mcp() -> None:
    """Run the MCP server over stdio."""
    # Loaded here and not at the top of the module: the MCP libraries take
    # longer to import than the rest of the command line together.
    import_module("itu_t_documents.mcp").main()


def auth() -> None:
    """Check whether TIES credentials are configured and usable."""
    settings = Settings()
    if not settings.has_credentials():
        raise AuthenticationError(f"no TIES credentials configured; set ITU_TIES_USERNAME and ITU_TIES_PASSWORD or store them in {settings.config_file}")
    with ItuHttpClient(settings) as client:
        client.authenticate()
    print("TIES login succeeded.")
