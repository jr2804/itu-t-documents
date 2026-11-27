"""The MCP server: its instructions, its tools and its entry point."""

from __future__ import annotations

from fastmcp import FastMCP

from itu_t_documents.mcp import catalogue, documents, download, meetings, sources

#: Instructions shown to the MCP client.
INSTRUCTIONS = """\
Access the documents of ITU-T study group meetings.

Documents are identified by study period, study group, meeting, document type
and number. The metadata of every meeting that was visited is kept in a local
SQLite database, so repeated questions are answered without contacting
www.itu.int again. Downloading a document needs TIES credentials.
"""

#: The MCP server instance.
mcp: FastMCP = FastMCP(
    name="itu-t-documents",
    instructions=INSTRUCTIONS,
)

mcp.tool(meetings.list_meetings)
mcp.tool(meetings.list_questions)
mcp.tool(documents.documents_for_question)
mcp.tool(documents.contributions_by_source)
mcp.tool(documents.search_documents)
mcp.tool(sources.top_sources)
mcp.tool(download.download_document)
mcp.tool(catalogue.list_periods)
mcp.tool(catalogue.list_study_groups)
mcp.tool(catalogue.list_structure)
mcp.tool(catalogue.search_structure)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()
