"""The MCP server of ITU-T Documents.

The server speaks the Model Context Protocol over stdio and offers the
capability of the package as tools for an AI agent. ``mcp`` is the server and
``main`` runs it::

    itu-t-documents mcp

The tools live in one module per group of questions. ``AGENTS.md`` next to
this file lists every tool with the API method and the CLI command it mirrors.

Nothing else in the package imports this package: the ``mcp`` command of the
CLI loads it when the command runs, so that the command line does not load
the MCP libraries.
"""

from __future__ import annotations

from itu_t_documents.mcp.server import INSTRUCTIONS, main, mcp

__all__ = ["INSTRUCTIONS", "main", "mcp"]
