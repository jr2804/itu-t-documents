"""Tests for the composition of the MCP server: its tools, its parity with the CLI and the API, and what the tools share."""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

import pytest

import itu_t_documents
from itu_t_documents.api import ItuDocuments
from itu_t_documents.cli import app as cli_app
from itu_t_documents.config.settings import Settings
from itu_t_documents.mcp import mcp
from itu_t_documents.mcp.server import INSTRUCTIONS, main
from itu_t_documents.mcp.support import open_api, resolve_period, sync_meetings
from itu_t_documents.models.study_periods import StudyPeriod
from tests.fakes import FakeClient

#: The tools whose question the CLI cannot ask yet. The list only shrinks.
WITHOUT_COMMAND: frozenset[str] = frozenset()

_ROW_RE = re.compile(r"^\|\s*`(?P<tool>[a-z_]+)`\s*\|\s*`(?P<owner>\w+)\.(?P<method>\w+)\(\)`\s*\|\s*(?P<command>[^|]+?)\s*\|\s*$", re.MULTILINE)


def test_every_tool_has_a_row_in_the_contract() -> None:
    """The server offers exactly the tools the contract lists."""
    tools = {tool.name for tool in asyncio.run(mcp.list_tools())}

    assert tools
    assert tools == set(_counterparts())


def test_every_tool_mirrors_the_api_and_the_cli() -> None:
    """The API method of every row exists and the CLI has its command, except for the listed tools."""
    counterparts = _counterparts()

    assert {tool for tool, (_, _, command) in counterparts.items() if command is None} == WITHOUT_COMMAND
    for tool, (owner_name, method, command) in counterparts.items():
        assert callable(getattr(getattr(itu_t_documents, owner_name), method)), tool
        if command is not None:
            assert command in cli_app.app._registered_commands, tool


def _counterparts() -> dict[str, tuple[str, str, str | None]]:
    """Read the table of the API method and the CLI command of every tool from the contract of the MCP server."""
    counterparts: dict[str, tuple[str, str, str | None]] = {}
    for match in _ROW_RE.finditer(_contract_file().read_text(encoding="utf-8")):
        command = match["command"].strip().strip("`").strip()
        counterparts[match["tool"]] = (match["owner"], match["method"], None if command.startswith("—") else command.split()[0])
    return counterparts


def _contract_file() -> Path:
    """Return the AGENTS.md of the MCP server."""
    return _package_dir() / "mcp" / "AGENTS.md"


def test_the_server_names_itself_and_shows_its_instructions() -> None:
    """The client sees the name of the package and what the server does."""
    assert mcp.name == "itu-t-documents"
    assert mcp.instructions == INSTRUCTIONS
    assert "TIES credentials" in INSTRUCTIONS


def test_main_runs_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """The entry point of the MCP server starts the server."""
    started: list[bool] = []
    monkeypatch.setattr(mcp, "run", lambda *args, **kwargs: started.append(True))

    main()

    assert started == [True]


def test_only_the_mcp_command_of_the_cli_loads_the_mcp_package() -> None:
    """No module of the package imports the MCP server; the CLI loads it by name."""
    references: dict[str, int] = {}
    for module_file in sorted(_package_dir().rglob("*.py")):
        relative = module_file.relative_to(_package_dir())
        if relative.parts[0] == "mcp":
            continue
        tree = ast.parse(module_file.read_text(encoding="utf-8"))
        count = sum(name.startswith("itu_t_documents.mcp") for node in ast.walk(tree) for name in _imported_names(node))
        if count:
            references[str(relative)] = count

    assert references == {"cli/startup.py": 1}


def _package_dir() -> Path:
    """Return the directory of the package."""
    return Path(__file__).parents[1] / "src" / "itu_t_documents"


def _imported_names(node: ast.AST) -> list[str]:
    """Return what an import statement or a string literal names; nothing for any other node."""
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return [node.module]
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def test_open_api_closes_the_package_after_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tool call gets the package with the resolved settings, closed when the call ends."""
    events: list[object] = []

    class FakeApi:
        """A stand-in for the API."""

        def close(self) -> None:
            """Record that the call ended."""
            events.append("closed")

    def open_package(settings: Settings) -> FakeApi:
        """Record the settings the tool passed and hand out the stand-in."""
        events.append(settings)
        return FakeApi()

    monkeypatch.setattr("itu_t_documents.mcp.support.ItuDocuments", open_package)

    with pytest.raises(RuntimeError, match="the tool failed"), open_api() as api:
        raise RuntimeError("the tool failed")

    assert isinstance(api, FakeApi)
    assert len(events) == 2
    assert isinstance(events[0], Settings)
    assert events[1] == "closed"


def test_resolve_period_with_an_explicit_label() -> None:
    """The tools accept an explicit study period and default to the current one."""
    assert resolve_period("2017-2020").label == "2017-2020"
    assert resolve_period(None) == StudyPeriod.current()


def test_sync_meetings_skips_an_invalid_meeting_code(tmp_path: Path, fake_client: FakeClient) -> None:
    """A meeting code that cannot be read is skipped."""
    with ItuDocuments(Settings(cache_dir=tmp_path), client=fake_client) as api:
        assert sync_meetings(api, 12, StudyPeriod(start_year=2025, end_year=2028), ["abc"]) == []
