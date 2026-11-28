"""Smoke tests for the package scaffold and its CLI wiring."""

from __future__ import annotations

import importlib
import runpy
from importlib.metadata import PackageNotFoundError

import pytest

import itu_t_documents
from itu_t_documents import __about__
from itu_t_documents.cli import app as cli_app
from itu_t_documents.cli import commands


def test_package_exposes_version() -> None:
    """Importing the package and its metadata module must work."""
    assert itu_t_documents.__version__
    assert __about__.__title__ == "itu_t_documents"


def test_package_names_its_home_and_its_documentation() -> None:
    """The metadata names the repository and the site of the documentation."""
    assert __about__.__url__ == "https://github.com/jr2804/itu-t-documents"
    assert __about__.__docs_url__ == "https://jr2804.github.io/itu-t-documents/"


def test_package_exports_the_public_api() -> None:
    """The package exports the objects of the public API."""
    assert itu_t_documents.ItuDocuments.__name__ == "ItuDocuments"
    assert itu_t_documents.DocumentRef.__name__ == "DocumentRef"
    assert itu_t_documents.DocType.CONTRIBUTION == "C"


def test_cli_version_uses_metadata() -> None:
    """The CLI reports the version of the package metadata."""
    assert cli_app.app.version == __about__.__version__
    assert cli_app.app.version


def test_the_version_falls_back_without_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """The package still reports a version when package metadata is unavailable."""

    def missing(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", missing)
    try:
        reloaded = importlib.reload(__about__)
        assert reloaded.__version__ == "0.0.0"
    finally:
        monkeypatch.undo()
        importlib.reload(__about__)


def test_cli_main_invokes_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """The console entry point delegates to the Cyclopts app."""
    invoked: list[bool] = []
    monkeypatch.setattr(cli_app, "app", lambda: invoked.append(True))

    cli_app.main()

    assert invoked == [True]


def test_dunder_main_invokes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """`python -m itu_t_documents` runs the CLI entry point."""
    invoked: list[bool] = []
    monkeypatch.setattr(cli_app, "main", lambda: invoked.append(True))

    runpy.run_module("itu_t_documents", run_name="__main__")

    assert invoked == [True]


def test_cli_registers_every_command() -> None:
    """Every command of the package is registered with the CLI."""
    registered = set(cli_app.app._registered_commands)

    assert {"auth", "documents", "download", "mcp", "meetings", "questions", "sync"} <= registered


def test_default_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The default command prints the welcome message."""
    commands.default()

    assert "itu-t-documents" in capsys.readouterr().out
